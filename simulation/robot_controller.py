from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Tuple

import pygame

from .config import CONTROL_CONFIG, GANTRY_CONFIG
from .environment import PCBAEnvironment
from .logging_system import AIStatus, ControlMode


@dataclass
class RobotTelemetry:
    gantry_x: float
    gantry_y: float
    control_mode: ControlMode
    ai_status: AIStatus
    ai_log: str


class RobotController:
    """
    Controls the camera gantry motion and safety behavior (the "body").

    Responsibilities:
    - Execute low-level (x, y) motion in board coordinates.
    - Support operator manual override (velocity and point-to-point).
    - Ensure mission-critical safety: return to (0, 0) on failures.

    Non-responsibilities (handled by the EmbodiedAgent):
    - Perception (YOLO / CV)
    - High-level reasoning (LLM)
    - mTrac logging
    """

    def __init__(
        self,
        environment: PCBAEnvironment,
    ) -> None:
        self.environment: PCBAEnvironment = environment

        # Board-local coordinate frame:
        # - (0, 0) is the board origin at its top-left corner
        # - Positions refer to the *center* of the gantry square
        self.position_board: pygame.math.Vector2 = pygame.math.Vector2(
            *GANTRY_CONFIG.home_position
        )
        self.target_board: pygame.math.Vector2 | None = None

        self.safe_return_active: bool = False
        self.control_mode: Literal["AI", "MANUAL"] = "AI"

        self._manual_direction: pygame.math.Vector2 = pygame.math.Vector2(0.0, 0.0)
        self._last_ai_status: AIStatus = "unknown"
        self._last_ai_log: str = ""

    def reset(self) -> None:
        self.position_board.update(*GANTRY_CONFIG.home_position)
        self.target_board = None
        self.safe_return_active = False
        self.control_mode = "AI"
        self._manual_direction.update(0.0, 0.0)
        self._last_ai_status = "unknown"
        self._last_ai_log = ""

    def set_manual_direction(self, dx: float, dy: float) -> None:
        self._manual_direction.update(dx, dy)

    def toggle_manual_mode(self) -> None:
        self.control_mode = "MANUAL" if self.control_mode == "AI" else "AI"
        self.target_board = None
        self._manual_direction.update(0.0, 0.0)

    def set_target_from_screen(self, screen_xy: Tuple[int, int]) -> None:
        if not self.environment.is_point_on_board(screen_xy):
            return
        bx, by = self.environment.screen_to_board((float(screen_xy[0]), float(screen_xy[1])))
        self.target_board = pygame.math.Vector2(bx, by)
        self._clamp_target_to_board()

    def set_target_board(self, x: float, y: float) -> None:
        self.target_board = pygame.math.Vector2(x, y)
        self._clamp_target_to_board()

    def set_ai_feedback(self, status: AIStatus, log: str) -> None:
        self._last_ai_status = status
        self._last_ai_log = log

    def enter_safe_return(self, reason: str) -> None:
        self.safe_return_active = True
        self.target_board = pygame.math.Vector2(*GANTRY_CONFIG.home_position)
        self._last_ai_status = "error"
        self._last_ai_log = reason

    def clear_safe_return_if_home(self) -> None:
        if self.safe_return_active and self._is_at_target(tolerance=1.5):
            self.safe_return_active = False
            self.target_board = None

    def get_gantry_rect(self) -> pygame.Rect:
        size: int = GANTRY_CONFIG.size
        half: int = size // 2
        screen_x, screen_y = self.environment.board_to_screen(
            (float(self.position_board.x), float(self.position_board.y))
        )
        return pygame.Rect(
            int(screen_x) - half,
            int(screen_y) - half,
            size,
            size,
        )

    def update_motion(self, dt_seconds: float) -> None:
        """Update gantry motion only (no AI, no perception)."""
        if self.safe_return_active:
            if self.target_board is None:
                self.target_board = pygame.math.Vector2(*GANTRY_CONFIG.home_position)
            self._move_towards_target(
                dt_seconds, speed=GANTRY_CONFIG.speed_pixels_per_second
            )
            self.clear_safe_return_if_home()
            return

        if self.control_mode == "MANUAL":
            self._update_manual(dt_seconds)
            return

        # AI mode: just move toward the last set target.
        self._move_towards_target(dt_seconds, speed=GANTRY_CONFIG.speed_pixels_per_second)

    def _update_manual(self, dt_seconds: float) -> None:
        # Manual velocity control (arrows/WASD) takes priority over point target.
        if self._manual_direction.length_squared() > 0.0:
            direction = self._manual_direction.normalize()
            step = direction * (CONTROL_CONFIG.manual_speed_pixels_per_second * dt_seconds)
            self.position_board += step
            self._clamp_position_to_board()
            self.target_board = None
            return

        # If user clicked a target while in MANUAL, we can still drive to it.
        self._move_towards_target(dt_seconds, speed=CONTROL_CONFIG.manual_speed_pixels_per_second)

    def _move_towards_target(self, dt_seconds: float, *, speed: float) -> None:
        if self.target_board is None:
            return

        direction = self.target_board - self.position_board
        distance: float = direction.length()
        if distance <= 0.0:
            return

        max_step: float = speed * dt_seconds
        if distance <= max_step:
            self.position_board.update(self.target_board.x, self.target_board.y)
        else:
            direction.scale_to_length(max_step)
            self.position_board += direction

        self._clamp_position_to_board()

    def _is_at_target(self, tolerance: float = 1.0) -> bool:
        if self.target_board is None:
            return True
        return self.position_board.distance_to(self.target_board) <= tolerance

    def _clamp_target_to_board(self) -> None:
        if self.target_board is None:
            return
        geom = self.environment.get_board_geometry()
        self.target_board.x = max(0.0, min(float(geom.width), float(self.target_board.x)))
        self.target_board.y = max(0.0, min(float(geom.height), float(self.target_board.y)))

    def _clamp_position_to_board(self) -> None:
        geom = self.environment.get_board_geometry()
        self.position_board.x = max(0.0, min(float(geom.width), float(self.position_board.x)))
        self.position_board.y = max(0.0, min(float(geom.height), float(self.position_board.y)))

    def get_telemetry(self) -> RobotTelemetry:
        mode: ControlMode = "SAFE_RETURN" if self.safe_return_active else (
            "MANUAL" if self.control_mode == "MANUAL" else "AI"
        )
        ai_status: AIStatus = self._last_ai_status if self.control_mode == "AI" else "unknown"
        ai_log: str = self._last_ai_log if self.control_mode == "AI" else ""
        return RobotTelemetry(
            gantry_x=float(self.position_board.x),
            gantry_y=float(self.position_board.y),
            control_mode=mode,
            ai_status=ai_status,
            ai_log=ai_log,
        )

