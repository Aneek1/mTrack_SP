from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, Tuple

import pygame

from .components import Component
from .environment import PCBAEnvironment
from .perception_types import CameraPatch, Detection


class VisionSystem(Protocol):
    def infer(self, patch: CameraPatch) -> List[Detection]:
        ...


class GroundTruthVisionSystem:
    """
    A drop-in VisionSystem that uses the digital twin (ground truth).

    This is the bridge step that makes the architecture feel like "YOLO now"
    while keeping the project runnable without ML dependencies.
    """

    def __init__(self, environment: PCBAEnvironment) -> None:
        self.environment: PCBAEnvironment = environment

    def infer(self, patch: CameraPatch) -> List[Detection]:
        x0, y0 = patch.origin_board_xy
        w, h = patch.size
        patch_board_rect = pygame.Rect(int(x0), int(y0), int(w), int(h))

        components: List[Component] = self.environment.get_components_in_board_rect(
            patch_board_rect
        )
        detections: List[Detection] = []
        for c in components:
            rect_board = self.environment.component_rect_to_board(c.rect)
            x1 = float(rect_board.left)
            y1 = float(rect_board.top)
            x2 = float(rect_board.right)
            y2 = float(rect_board.bottom)
            detections.append(
                Detection(
                    # Perception should NOT magically reveal defects. It only "detects components".
                    label="component",
                    confidence=1.0,
                    bbox_board_xyxy=(x1, y1, x2, y2),
                    component_id=c.component_id,
                    attributes={
                        # Provide mild appearance info, but not the ground-truth defect label.
                        "tilt_degrees": float(c.tilt_degrees),
                    },
                    source="ground_truth",
                )
            )
        return detections


class YoloVisionSystem:
    """
    Optional Ultralytics YOLO-based vision backend.

    Notes:
    - This requires `ultralytics` + `numpy` to be installed.
    - It expects a model trained on your synthetic or real PCBA dataset.
    - Output boxes are mapped from patch pixel coords to board coords using
      patch.origin_board_xy.
    """

    def __init__(self, weights_path: str, class_names: Dict[int, str] | None = None) -> None:
        try:
            from ultralytics import YOLO  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "Ultralytics not installed. Install with: pip install -r requirements-yolo.txt"
            ) from exc

        self._YOLO = YOLO
        self.model = YOLO(weights_path)
        self.class_names: Dict[int, str] | None = class_names

    def infer(self, patch: CameraPatch) -> List[Detection]:
        try:
            import numpy as np  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise RuntimeError("numpy not installed. Install requirements-yolo.txt") from exc

        surf = patch.surface
        w, h = surf.get_size()
        raw = pygame.image.tostring(surf, "RGB")
        img = np.frombuffer(raw, dtype=np.uint8).reshape((h, w, 3))

        results = self.model.predict(img, verbose=False)
        if not results:
            return []

        r0 = results[0]
        boxes = getattr(r0, "boxes", None)
        if boxes is None:
            return []

        x0, y0 = patch.origin_board_xy
        detections: List[Detection] = []
        # Ultralytics Boxes API: xyxy, cls, conf
        for i in range(len(boxes)):
            b = boxes[i]
            xyxy = b.xyxy[0].tolist()
            conf = float(b.conf[0].item()) if hasattr(b.conf[0], "item") else float(b.conf[0])
            cls = int(b.cls[0].item()) if hasattr(b.cls[0], "item") else int(b.cls[0])
            label = self.class_names.get(cls, str(cls)) if self.class_names else str(cls)
            x1p, y1p, x2p, y2p = (float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3]))
            # Map patch pixel coords to board coords
            detections.append(
                Detection(
                    label=label,
                    confidence=conf,
                    bbox_board_xyxy=(x0 + x1p, y0 + y1p, x0 + x2p, y0 + y2p),
                    source="yolo",
                )
            )
        return detections

