from __future__ import annotations

import json
from typing import List

import pygame

from .config import AI_CONFIG, CAMERA_CONFIG, CONTROL_CONFIG
from .environment import PCBAEnvironment
from .inspection_ai import AIDecisionTrace, InspectionAI
from .logging_system import MTracLogger
from .robot_controller import RobotController, RobotTelemetry
from .perception_types import CameraPatch, Detection
from .path_planner import AStarPlanner
from .vision_system import GroundTruthVisionSystem, VisionSystem


class EmbodiedAgent:
    """
    High-level wrapper that makes the architecture feel like an embodied AI:

    - The **world** is the `PCBAEnvironment` (digital twin of the board).
    - The **brain** is `InspectionAI`.
    - The **body** is `RobotController` (gantry motion, safety, low-level control).
    - The **nervous system** is the pygame event+keyboard layer that calls into this agent.
    """

    def __init__(self, environment: PCBAEnvironment) -> None:
        self.environment: PCBAEnvironment = environment
        self.logger: MTracLogger = MTracLogger()
        self.brain: InspectionAI = InspectionAI(
            simulated_api_failure_rate=AI_CONFIG.simulated_api_failure_rate
        )
        self.vision: VisionSystem = GroundTruthVisionSystem(environment=self.environment)
        self.body: RobotController = RobotController(environment=self.environment)

        self._ai_replan_accumulator: float = 0.0
        self.last_camera_patch: CameraPatch | None = None
        self.last_detections: List[Detection] = []
        self.last_ai_trace: AIDecisionTrace | None = None

        # Search / inspection state (what the agent has *learned* so far)
        self.inspection_results: dict[str, str] = {}  # component_id -> PASS/FAIL
        self.seen_components: set[str] = set()
        self._dwell_seconds: dict[str, float] = {}
        self._dwell_threshold_s: float = 0.6

        # A* path planning / waypoint following
        geom = self.environment.get_board_geometry()
        self.planner = AStarPlanner((geom.width, geom.height))
        self._current_path: List[tuple[float, float]] = []
        self._current_goal: str | None = None  # component_id or "SCAN"
        self._scan_waypoints: List[tuple[float, float]] = self._build_scan_waypoints()
        self._scan_index: int = 0

    # -------- Sense / Decide / Act orchestration --------

    def step(self, dt_seconds: float) -> None:
        """
        Advance the embodied agent by one control cycle.

        Internally this:
        - Senses the world through the body (gantry + environment).
        - Perceives with a vision system (ground-truth or YOLO).
        - Decides using the brain (LLM placeholder).
        - Acts by commanding the body.
        - Logs into mTrac.
        """
        # 1) SENSE: get current pose (board coords)
        telemetry = self.body.get_telemetry()
        gantry_xy = (telemetry.gantry_x, telemetry.gantry_y)

        # 2) PERCEIVE: render camera patch + run detection
        patch = self.environment.render_camera_patch(
            gantry_center_board_xy=gantry_xy,
            size=(CAMERA_CONFIG.fov_width, CAMERA_CONFIG.fov_height),
        )
        self.last_camera_patch = patch
        detections = self.vision.infer(patch)
        self.last_detections = detections

        # Update what we've "seen" (discovery is local to the FOV)
        for det in detections:
            if det.component_id:
                self.seen_components.add(det.component_id)

        # If we're hovering on a component, dwell and only then decide PASS/FAIL.
        self._update_dwell_and_inspect(dt_seconds, detections)

        # 3) DECIDE (AI mode): use A* search + coverage scan; no instant defect reveal.
        if self.body.control_mode == "AI" and not self.body.safe_return_active:
            self._ai_replan_accumulator += dt_seconds
            should_replan = (
                self.body.target_board is None
                or not self._current_path
                or self._ai_replan_accumulator >= (1.0 / max(0.1, CONTROL_CONFIG.ai_replan_hz))
            )
            if should_replan:
                self._ai_replan_accumulator = 0.0
                self._plan_next_goal_and_path(current_xy=gantry_xy, detections=detections)

        # 4) ACT: update motion
        self.body.update_motion(dt_seconds)

        # 5) LOG: one row per step; PASS/FAIL only after inspection completes
        self._log_step(detections)

    def _build_scan_waypoints(self) -> List[tuple[float, float]]:
        geom = self.environment.get_board_geometry()
        cs = self.planner.config.cell_size
        margin = cs
        xs = list(range(margin, geom.width - margin, cs * 3))
        ys = list(range(margin, geom.height - margin, cs * 2))
        if not xs:
            xs = [geom.width / 2.0]
        if not ys:
            ys = [geom.height / 2.0]

        wps: List[tuple[float, float]] = []
        flip = False
        for y in ys:
            row = [(float(x), float(y)) for x in xs]
            if flip:
                row.reverse()
            wps.extend(row)
            flip = not flip
        return wps

    def _plan_next_goal_and_path(self, *, current_xy: tuple[float, float], detections: List[Detection]) -> None:
        # Choose next uninspected seen component if available; else keep scanning.
        candidates = [cid for cid in sorted(self.seen_components) if cid not in self.inspection_results]
        goal_xy: tuple[float, float]
        goal_name: str

        if candidates:
            goal_name = candidates[0]
            # If it's currently detected, use the detected bbox center; else keep scanning until rediscovered.
            det = next((d for d in detections if d.component_id == goal_name), None)
            if det is not None:
                goal_xy = det.center_board()
            else:
                goal_name = "SCAN"
                goal_xy = self._scan_waypoints[self._scan_index % len(self._scan_waypoints)]
                self._scan_index += 1
        else:
            goal_name = "SCAN"
            goal_xy = self._scan_waypoints[self._scan_index % len(self._scan_waypoints)]
            self._scan_index += 1

        keepouts = self.environment.get_keepout_rects_board(margin=12)
        blocked = self.planner.build_blocked_cells(keepouts)
        path = self.planner.plan(current_xy, goal_xy, blocked=blocked)

        # Reduce path density: keep every Nth point to make motion smoother
        thin: List[tuple[float, float]] = []
        stride = 2
        for i, p in enumerate(path):
            if i % stride == 0 or i == len(path) - 1:
                thin.append((float(p[0]), float(p[1])))

        self._current_goal = goal_name
        self._current_path = thin
        if self._current_path:
            nx, ny = self._current_path[0]
            self.body.set_target_board(nx, ny)
            self.body.set_ai_feedback(
                "moving",
                f"A*: goal={goal_name} path_pts={len(self._current_path)} (defects unknown until hover)",
            )

    def _update_dwell_and_inspect(self, dt: float, detections: List[Detection]) -> None:
        telemetry = self.body.get_telemetry()
        gantry_xy = (telemetry.gantry_x, telemetry.gantry_y)
        under = [d for d in detections if d.contains_point_board(gantry_xy) and d.component_id]
        if not under:
            return

        det = under[0]
        cid = det.component_id
        if cid is None or cid in self.inspection_results:
            return

        self._dwell_seconds[cid] = self._dwell_seconds.get(cid, 0.0) + dt
        if self._dwell_seconds[cid] < self._dwell_threshold_s:
            self.body.set_ai_feedback("inspecting", f"Hovering on {cid} ({self._dwell_seconds[cid]:.2f}s/{self._dwell_threshold_s:.2f}s)")
            return

        # "Inspection classifier": in this sim, consult ground truth ONLY after hover completes.
        comp = self.environment.get_component_by_id(cid)
        if comp is None:
            return
        self.inspection_results[cid] = "FAIL" if comp.is_defective else "PASS"
        self.body.set_ai_feedback("inspecting", f"Inspected {cid} -> {self.inspection_results[cid]}")

    def _log_step(self, detections: List[Detection]) -> None:
        profile = self.environment.profile
        telemetry = self.body.get_telemetry()
        gantry_xy = (telemetry.gantry_x, telemetry.gantry_y)

        under_gantry = [d for d in detections if d.contains_point_board(gantry_xy)]
        if not under_gantry:
            self.logger.log(
                component_id="NONE",
                pass_fail="UNKNOWN",
                profile_id=profile.profile_id,
                sku=profile.sku,
                revision=profile.revision,
                board_serial=profile.board_serial,
                gantry_x=telemetry.gantry_x,
                gantry_y=telemetry.gantry_y,
                control_mode=telemetry.control_mode,
                ai_status=telemetry.ai_status,
                ai_log=telemetry.ai_log,
            )
            return

        for det in under_gantry:
            attrs = det.attributes or {}
            if "is_defective" in attrs and isinstance(attrs["is_defective"], bool):
                pass_fail = "FAIL" if attrs["is_defective"] else "PASS"
            else:
                pass_fail = "UNKNOWN"

            self.logger.log(
                component_id=det.component_id or det.label,
                pass_fail=pass_fail,
                profile_id=profile.profile_id,
                sku=profile.sku,
                revision=profile.revision,
                board_serial=profile.board_serial,
                gantry_x=telemetry.gantry_x,
                gantry_y=telemetry.gantry_y,
                control_mode=telemetry.control_mode,
                ai_status=telemetry.ai_status,
                ai_log=telemetry.ai_log,
            )

    # -------- Control interfaces (for UI / operator) --------

    def handle_continuous_keyboard(self, pressed: pygame.key.ScancodeWrapper) -> None:
        dx: float = 0.0
        dy: float = 0.0
        if pressed[pygame.K_LEFT] or pressed[pygame.K_a]:
            dx -= 1.0
        if pressed[pygame.K_RIGHT] or pressed[pygame.K_d]:
            dx += 1.0
        if pressed[pygame.K_UP] or pressed[pygame.K_w]:
            dy -= 1.0
        if pressed[pygame.K_DOWN] or pressed[pygame.K_s]:
            dy += 1.0
        self.body.set_manual_direction(dx, dy)

    def handle_discrete_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                self.body.toggle_manual_mode()
            elif event.key == pygame.K_c:
                self.environment.reset_board()
                self.body.reset()
            elif event.key == pygame.K_h:
                self.body.reset()
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            position = event.pos
            if self.environment.handle_mouse_click(position):
                self.body.reset()
            elif self.body.control_mode == "MANUAL" and self.environment.is_point_on_board(position):
                self.body.set_target_from_screen(position)

    # -------- Introspection for rendering / logging --------

    def get_gantry_rect(self) -> pygame.Rect:
        return self.body.get_gantry_rect()

    def get_telemetry(self) -> RobotTelemetry:
        return self.body.get_telemetry()

    def build_overlay_lines(self) -> List[str]:
        profile = self.environment.profile
        telemetry = self.get_telemetry()
        target = self.body.target_board
        target_str = "None" if target is None else f"({target.x:.1f}, {target.y:.1f})"

        perception_src = (
            "YOLO" if (self.last_detections and self.last_detections[0].source == "yolo") else "ground_truth"
        )

        lines: List[str] = [
            f"Profile: {profile.sku} rev {profile.revision} | {profile.board_serial}",
            f"Seed: {profile.seed} | Profile_ID: {profile.profile_id}",
            f"Mode: {telemetry.control_mode} | Pose(board): ({telemetry.gantry_x:.1f}, {telemetry.gantry_y:.1f})",
            f"Target(board): {target_str}",
            "Controls: SPACE AI/MANUAL | WASD/arrows move | click board sets target (MANUAL)",
            "High-mix: C or button | Home: H | Quit: ESC",
            "",
            f"Perception: {perception_src} | detections={len(self.last_detections)}",
        ]

        for det in self.last_detections[:6]:
            x1, y1, x2, y2 = det.bbox_board_xyxy
            did = det.component_id or det.label
            lines.append(
                f"- {did} | {det.label} conf={det.confidence:.2f} bbox=({x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f})"
            )

        lines.append("")
        lines.append("LLM Prompt Hub → JSON Command")
        if self.last_ai_trace is None:
            if telemetry.ai_status != "unknown":
                lines.append(f"AI: {telemetry.ai_status} | {telemetry.ai_log}")
            else:
                lines.append("AI: (no decision yet)")
            return lines

        trace = self.last_ai_trace
        sys_first = trace.payload.system.strip().splitlines()[0] if trace.payload.system.strip() else ""
        lines.append(f"System: {sys_first}")
        lines.append(f"Schema keys: {list(trace.payload.json_schema.get('properties', {}).keys())}")

        obs = trace.payload.observation
        gp = obs.get("gantry_position", {})
        lines.append(f"Obs: gantry=({gp.get('x')},{gp.get('y')}) visible={len(obs.get('visible_components', []))}")

        # Raw JSON string from the "LLM"
        raw = trace.raw_text.strip()
        if len(raw) > 220:
            raw = raw[:220] + "..."
        lines.append(f"Raw JSON: {raw}")

        cmd = trace.command
        lines.append(f"Parsed: status={cmd['status']} move_to=({cmd['move_to'][0]:.1f},{cmd['move_to'][1]:.1f})")
        log_msg = cmd["log"]
        if len(log_msg) > 160:
            log_msg = log_msg[:160] + "..."
        lines.append(f"Log: {log_msg}")
        return lines

