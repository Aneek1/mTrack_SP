from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .body import RobotBody
from .brain import AIDecisionTrace, InspectionAI, VisibleComponent
from .planner import AStarPlanner
from .vision import CameraFOV, Detection, GroundTruthVisionSystem, VisionSystem
from .world import PCBAWorld


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class AgentConfig:
    fov_size: Tuple[int, int] = (320, 240)
    dwell_threshold_s: float = 0.6
    ai_replan_hz: float = 2.0


class HighMixInspectionAgent:
    """
    Headless embodied AI loop:
    - Sense: body pose
    - Perceive: vision detections in camera FOV
    - Decide: A* search + scan policy + (optional) LLM trace
    - Act: command body target
    - Learn: only decide PASS/FAIL after hover dwell completes
    """

    def __init__(
        self,
        *,
        world: PCBAWorld,
        body: RobotBody,
        ai: InspectionAI,
        vision: VisionSystem | None = None,
        config: AgentConfig | None = None,
    ) -> None:
        self.world = world
        self.body = body
        self.ai = ai
        self.vision: VisionSystem = vision or GroundTruthVisionSystem(world)
        self.config = config or AgentConfig()

        self.planner = AStarPlanner((self.world.width, self.world.height))

        self.seen_components: set[str] = set()
        self.inspection_results: Dict[str, str] = {}
        self._dwell_s: Dict[str, float] = {}

        self._ai_accum: float = 0.0
        self._scan_waypoints: List[Tuple[float, float]] = self._build_scan_waypoints()
        self.scan_index: int = 0
        self.planned_path: List[Tuple[float, float]] = []
        self.current_goal: Optional[str] = None

        self.last_ai_trace: Optional[AIDecisionTrace] = None
        self.thought_log_lines: List[str] = []

    def reset_for_new_profile(self) -> None:
        self.seen_components.clear()
        self.inspection_results.clear()
        self._dwell_s.clear()
        self._ai_accum = 0.0
        # Rebuild planner with updated board dimensions
        self.planner = AStarPlanner((self.world.width, self.world.height))
        self._scan_waypoints = self._build_scan_waypoints()
        self.scan_index = 0
        self.planned_path = []
        self.current_goal = None
        self.last_ai_trace = None
        self.thought_log_lines = []
        # Update body bounds and reset position
        self.body.board_w = float(self.world.width)
        self.body.board_h = float(self.world.height)
        self.body.reset()

    def step(self, dt: float) -> Dict[str, Any]:
        # 1) sense
        pose = (self.body.state.x, self.body.state.y)

        # 2) perceive
        fov = self._compute_fov(pose)
        detections = self.vision.infer(fov)
        for d in detections:
            if d.component_id:
                self.seen_components.add(d.component_id)

        # dwell/inspect only when hovering
        self._update_dwell_and_inspect(dt, detections)

        # 3) decide
        if self.body.state.mode == "AI":
            self._ai_accum += dt
            if (
                self.body.state.target is None
                or not self.planned_path
                or self._ai_accum >= (1.0 / max(0.1, self.config.ai_replan_hz))
            ):
                self._ai_accum = 0.0
                self._plan_next(pose, detections)

        # 4) act
        self.body.step_motion(dt)

        # 5) update thought log (human-readable)
        self.thought_log_lines = self._build_thought_log(detections)

        return {
            "server_time_utc": now_utc_iso(),
            "pose": {"x": self.body.state.x, "y": self.body.state.y},
            "target": self.body.state.target,
            "mode": self.body.state.mode,
            "ai_status": self.body.state.ai_status,
            "ai_log": self.body.state.ai_log,
            "fov": {"origin": fov.origin, "size": fov.size},
            "detections": detections,
            "planned_path": self.planned_path,
            "scan_index": self.scan_index,
        }

    def _compute_fov(self, pose: Tuple[float, float]) -> CameraFOV:
        cx, cy = pose
        w, h = self.config.fov_size
        x0 = cx - w / 2.0
        y0 = cy - h / 2.0
        x0 = max(0.0, min(float(self.world.width - w), x0))
        y0 = max(0.0, min(float(self.world.height - h), y0))
        return CameraFOV(origin=(x0, y0), size=(w, h))

    def _build_scan_waypoints(self) -> List[Tuple[float, float]]:
        cs = self.planner.config.cell_size
        margin = cs
        xs = list(range(margin, max(margin + 1, self.world.width - margin), cs * 3))
        ys = list(range(margin, max(margin + 1, self.world.height - margin), cs * 2))
        if not xs:
            xs = [int(self.world.width / 2)]
        if not ys:
            ys = [int(self.world.height / 2)]
        wps: List[Tuple[float, float]] = []
        flip = False
        for y in ys:
            row = [(float(x), float(y)) for x in xs]
            if flip:
                row.reverse()
            wps.extend(row)
            flip = not flip
        return wps

    def _plan_next(self, pose: Tuple[float, float], detections: List[Detection]) -> None:
        # prefer uninspected components we've discovered
        candidates = [c for c in sorted(self.seen_components) if c not in self.inspection_results]
        goal_xy: Tuple[float, float]
        is_component_goal = False
        if candidates:
            goal_cid = candidates[0]
            det = next((d for d in detections if d.component_id == goal_cid), None)
            if det is not None:
                goal_xy = det.center()
                self.current_goal = goal_cid
                is_component_goal = True
            else:
                # not currently visible -> keep scanning
                goal_xy = self._scan_waypoints[self.scan_index % len(self._scan_waypoints)]
                self.scan_index += 1
                self.current_goal = "SCAN"
        else:
            goal_xy = self._scan_waypoints[self.scan_index % len(self._scan_waypoints)]
            self.scan_index += 1
            self.current_goal = "SCAN"

        blocked = self.planner.build_blocked_cells(self.world.keepouts(margin=12.0))
        path = self.planner.plan(pose, goal_xy, blocked=blocked)
        thin: List[Tuple[float, float]] = []
        for i, p in enumerate(path):
            if i % 2 == 0 or i == len(path) - 1:
                thin.append((float(p[0]), float(p[1])))
        # For component goals, replace the last waypoint with the exact component center
        if is_component_goal and thin:
            thin[-1] = goal_xy
        self.planned_path = thin
        if self.planned_path:
            nx, ny = self.planned_path[0]
            self.body.set_target(nx, ny)
            self.body.set_ai_feedback("moving", f"A*: goal={self.current_goal} path_pts={len(self.planned_path)}")

        # Optional: create an LLM trace for the thought log (doesn't drive motion yet)
        try:
            visible_components: List[VisibleComponent] = []
            for det in detections:
                x1, y1, x2, y2 = det.bbox_xyxy
                visible_components.append(
                    {
                        "id": det.component_id or det.label,
                        "center_board": det.center(),
                        "approx_size": (float(x2 - x1), float(y2 - y1)),
                        "appearance": det.attributes or {},
                        "label": det.label,
                        "confidence": float(det.confidence),
                        "bbox_board_xyxy": det.bbox_xyxy,
                    }
                )
            prof = self.world.profile
            self.last_ai_trace = self.ai.decide_next_action_with_trace(
                visible_components=visible_components,
                gantry_position=pose,
                board_geometry=(self.world.width, self.world.height),
                product_profile={
                    "profile_id": prof.profile_id,
                    "sku": prof.sku,
                    "revision": prof.revision,
                    "board_serial": prof.board_serial,
                    "seed": prof.seed,
                    "created_utc": prof.created_utc,
                },
            )
        except Exception:
            self.last_ai_trace = None

    def _update_dwell_and_inspect(self, dt: float, detections: List[Detection]) -> None:
        pose = (self.body.state.x, self.body.state.y)
        # Use proximity-based detection: robot within component bbox OR within
        # a small margin (to handle tiny components from test generator)
        margin = 15.0  # px tolerance for "hovering over" a component
        under: List[Detection] = []
        for d in detections:
            if not d.component_id:
                continue
            # Check strict containment first
            if d.contains_point(pose):
                under.append(d)
                continue
            # Proximity check: within margin of the component center
            cx, cy = d.center()
            dx = abs(pose[0] - cx)
            dy = abs(pose[1] - cy)
            if dx <= margin and dy <= margin:
                under.append(d)
        if not under:
            return
        det = under[0]
        cid = det.component_id
        if cid is None or cid in self.inspection_results:
            return

        self._dwell_s[cid] = self._dwell_s.get(cid, 0.0) + dt
        if self._dwell_s[cid] < self.config.dwell_threshold_s:
            self.body.set_ai_feedback("inspecting", f"Hovering on {cid} ({self._dwell_s[cid]:.2f}s/{self.config.dwell_threshold_s:.2f}s)")
            return

        comp = self.world.component_by_id(cid)
        if comp is None:
            return
        self.inspection_results[cid] = "FAIL" if comp.is_defective else "PASS"
        self.body.set_ai_feedback("inspecting", f"Inspected {cid} -> {self.inspection_results[cid]}")

    def _build_thought_log(self, detections: List[Detection]) -> List[str]:
        prof = self.world.profile
        s = self.body.state
        goal = self.current_goal or "None"
        tgt = "None" if s.target is None else f"({s.target[0]:.1f},{s.target[1]:.1f})"
        lines: List[str] = [
            f"Profile: {prof.sku} rev {prof.revision} | {prof.board_serial}",
            f"Mode: {s.mode} Pose(board): ({s.x:.1f},{s.y:.1f}) Target: {tgt}",
            f"Search: goal={goal} seen={len(self.seen_components)} inspected={len(self.inspection_results)} scan_index={self.scan_index}",
            "",
            f"Perception: detections={len(detections)} (defects unknown until dwell completes)",
        ]
        for d in detections[:6]:
            x1, y1, x2, y2 = d.bbox_xyxy
            lines.append(f"- {d.component_id or d.label} | conf={d.confidence:.2f} bbox=({x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f})")
        lines.append("")
        lines.append("LLM Prompt Hub (trace)")
        if self.last_ai_trace is None:
            lines.append("(no trace)")
            return lines
        tr = self.last_ai_trace
        sys_first = tr.payload.system.strip().splitlines()[0] if tr.payload.system.strip() else ""
        raw = tr.raw_text.strip()
        if len(raw) > 220:
            raw = raw[:220] + "..."
        lines.append(f"System: {sys_first}")
        lines.append(f"Schema keys: {list(tr.payload.json_schema.get('properties', {}).keys())}")
        lines.append(f"Raw JSON: {raw}")
        cmd = tr.command
        lines.append(f"Parsed: status={cmd['status']} move_to=({cmd['move_to'][0]:.1f},{cmd['move_to'][1]:.1f})")
        return lines

