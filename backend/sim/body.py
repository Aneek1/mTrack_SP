from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Tuple


Mode = Literal["AI", "MANUAL", "SAFE_RETURN"]


@dataclass
class BodyState:
    x: float = 0.0
    y: float = 0.0
    target: Optional[Tuple[float, float]] = None
    mode: Mode = "AI"
    safe_return_active: bool = False
    manual_dx: int = 0
    manual_dy: int = 0
    ai_status: str = "unknown"
    ai_log: str = ""


class RobotBody:
    def __init__(
        self,
        *,
        board_size: Tuple[int, int],
        speed_px_s: float = 200.0,
        manual_speed_px_s: float = 260.0,
    ) -> None:
        self.board_w: float = float(board_size[0])
        self.board_h: float = float(board_size[1])
        self.speed: float = float(speed_px_s)
        self.manual_speed: float = float(manual_speed_px_s)
        self.state: BodyState = BodyState()

    def reset(self) -> None:
        self.state = BodyState()

    def toggle_mode(self) -> None:
        if self.state.mode == "MANUAL":
            self.state.mode = "AI"
        else:
            self.state.mode = "MANUAL"
        self.state.target = None
        self.state.manual_dx = 0
        self.state.manual_dy = 0

    def set_manual_velocity(self, dx: int, dy: int) -> None:
        self.state.manual_dx = int(max(-1, min(1, dx)))
        self.state.manual_dy = int(max(-1, min(1, dy)))

    def set_target(self, x: float, y: float) -> None:
        self.state.target = (float(x), float(y))
        self._clamp_target()

    def set_ai_feedback(self, status: str, log: str) -> None:
        self.state.ai_status = status
        self.state.ai_log = log

    def enter_safe_return(self, reason: str) -> None:
        self.state.mode = "SAFE_RETURN"
        self.state.safe_return_active = True
        self.state.target = (0.0, 0.0)
        self.state.ai_status = "error"
        self.state.ai_log = reason

    def home(self) -> None:
        self.state.x = 0.0
        self.state.y = 0.0
        self.state.target = None
        self.state.safe_return_active = False
        if self.state.mode == "SAFE_RETURN":
            self.state.mode = "AI"

    def step_motion(self, dt: float) -> None:
        if dt <= 0:
            return

        if self.state.mode == "MANUAL":
            self._step_manual(dt)
            return

        # AI or SAFE_RETURN: move toward target (if any)
        if self.state.target is None:
            return
        self._step_toward_target(dt, speed=self.speed)

        if self.state.mode == "SAFE_RETURN" and self._at_target():
            # Once at home, allow resume into AI
            self.state.safe_return_active = False
            self.state.mode = "AI"
            self.state.target = None

    def _step_manual(self, dt: float) -> None:
        dx = float(self.state.manual_dx)
        dy = float(self.state.manual_dy)
        if dx == 0.0 and dy == 0.0:
            # If a point target exists, manual can still follow it
            if self.state.target is not None:
                self._step_toward_target(dt, speed=self.manual_speed)
            return

        # normalize
        mag = (dx * dx + dy * dy) ** 0.5
        dx /= mag
        dy /= mag
        self.state.x += dx * self.manual_speed * dt
        self.state.y += dy * self.manual_speed * dt
        self._clamp_position()
        self.state.target = None

    def _step_toward_target(self, dt: float, *, speed: float) -> None:
        assert self.state.target is not None
        tx, ty = self.state.target
        vx = tx - self.state.x
        vy = ty - self.state.y
        dist = (vx * vx + vy * vy) ** 0.5
        if dist <= 1e-6:
            return
        max_step = speed * dt
        if dist <= max_step:
            self.state.x = tx
            self.state.y = ty
        else:
            self.state.x += (vx / dist) * max_step
            self.state.y += (vy / dist) * max_step
        self._clamp_position()

    def _at_target(self, tol: float = 1.5) -> bool:
        if self.state.target is None:
            return True
        tx, ty = self.state.target
        dx = self.state.x - tx
        dy = self.state.y - ty
        return (dx * dx + dy * dy) ** 0.5 <= tol

    def _clamp_target(self) -> None:
        if self.state.target is None:
            return
        tx, ty = self.state.target
        self.state.target = (
            max(0.0, min(self.board_w, tx)),
            max(0.0, min(self.board_h, ty)),
        )

    def _clamp_position(self) -> None:
        self.state.x = max(0.0, min(self.board_w, self.state.x))
        self.state.y = max(0.0, min(self.board_h, self.state.y))

