from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import pygame


@dataclass(frozen=True)
class CameraPatch:
    """A virtual camera frame cropped from the board render."""

    surface: pygame.Surface
    origin_board_xy: Tuple[float, float]  # top-left of patch in board coords
    size: Tuple[int, int]  # (w, h) in pixels == board units for this sim


@dataclass(frozen=True)
class Detection:
    """
    A perception output in board coordinates.

    bbox_board_xyxy uses board-local coordinates (same frame as RobotController).
    """

    label: str
    confidence: float
    bbox_board_xyxy: Tuple[float, float, float, float]  # x1, y1, x2, y2
    component_id: Optional[str] = None
    attributes: Dict[str, Any] | None = None
    source: str = "unknown"

    def center_board(self) -> Tuple[float, float]:
        x1, y1, x2, y2 = self.bbox_board_xyxy
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    def contains_point_board(self, xy: Tuple[float, float]) -> bool:
        x, y = xy
        x1, y1, x2, y2 = self.bbox_board_xyxy
        return x1 <= x <= x2 and y1 <= y <= y2

