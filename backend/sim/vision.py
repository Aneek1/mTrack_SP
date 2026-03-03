from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Tuple

from .geometry import Rect
from .world import PCBAWorld


@dataclass(frozen=True)
class CameraFOV:
    origin: Tuple[float, float]  # top-left in board coords
    size: Tuple[int, int]  # (w, h)

    def rect(self) -> Rect:
        return Rect(self.origin[0], self.origin[1], float(self.size[0]), float(self.size[1]))


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    bbox_xyxy: Tuple[float, float, float, float]
    component_id: Optional[str] = None
    attributes: Dict[str, Any] | None = None
    source: str = "unknown"

    def center(self) -> Tuple[float, float]:
        x1, y1, x2, y2 = self.bbox_xyxy
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    def contains_point(self, p: Tuple[float, float]) -> bool:
        x, y = p
        x1, y1, x2, y2 = self.bbox_xyxy
        return x1 <= x <= x2 and y1 <= y <= y2


class VisionSystem(Protocol):
    def infer(self, fov: CameraFOV) -> List[Detection]:
        ...


class GroundTruthVisionSystem:
    """
    Headless 'vision' that uses the world to produce component detections.
    Crucially: it does NOT reveal defect labels.
    """

    def __init__(self, world: PCBAWorld) -> None:
        self.world = world

    def infer(self, fov: CameraFOV) -> List[Detection]:
        fov_rect = fov.rect()
        out: List[Detection] = []
        for c in self.world.components:
            if not c.rect.intersects(fov_rect):
                continue
            x1 = c.rect.left
            y1 = c.rect.top
            x2 = c.rect.right
            y2 = c.rect.bottom
            out.append(
                Detection(
                    label="component",
                    confidence=1.0,
                    bbox_xyxy=(x1, y1, x2, y2),
                    component_id=c.component_id,
                    attributes={"tilt_degrees": float(c.tilt_degrees)},
                    source="ground_truth",
                )
            )
        return out


class YoloVisionSystem:
    """
    Optional YOLO backend. This is a placeholder adapter.

    In this repo we keep it optional; it will raise if ultralytics isn't installed.
    """

    def __init__(self, world: PCBAWorld, weights_path: str) -> None:
        self.world = world
        self.weights_path = weights_path
        try:
            from ultralytics import YOLO  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("ultralytics not installed; install requirements-yolo.txt") from exc
        self.model = YOLO(weights_path)

    def infer(self, fov: CameraFOV) -> List[Detection]:
        # TODO: replace with real image rendering + YOLO inference.
        # For now, fall back to ground truth detections to keep runtime stable.
        return GroundTruthVisionSystem(self.world).infer(fov)

