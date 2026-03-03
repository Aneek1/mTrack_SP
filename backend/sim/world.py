from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any

from .geometry import Rect
from .test_generator import TestCase, DefectInstance


@dataclass(frozen=True)
class ProductProfile:
    profile_id: int
    sku: str
    revision: str
    board_serial: str
    seed: int
    created_utc: str


@dataclass
class ComponentSpec:
    component_id: str
    rect: Rect
    is_defective: bool
    tilt_degrees: float
    defect_details: Optional[Dict[str, Any]] = None


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PCBAWorld:
    def __init__(
        self,
        *,
        width: int = 840,
        height: int = 520,
        min_components: int = 5,
        max_components: int = 10,
        component_size: Tuple[int, int] = (60, 30),
    ) -> None:
        self.width: int = int(width)
        self.height: int = int(height)
        self.min_components: int = int(min_components)
        self.max_components: int = int(max_components)
        self.component_w: int = int(component_size[0])
        self.component_h: int = int(component_size[1])

        self._profile_counter: int = 0
        self.profile: ProductProfile = self._new_profile()
        self._rng: random.Random = random.Random(self.profile.seed)

        self.components: List[ComponentSpec] = []
        self._generate_components()

    def _new_profile(self) -> ProductProfile:
        self._profile_counter += 1
        seed = random.randint(1, 2_147_483_647)
        sku = f"SKU-{random.randint(100, 999)}"
        revision = random.choice(["A", "B", "C"])
        board_serial = f"BOARD-{self._profile_counter:04d}"
        return ProductProfile(
            profile_id=self._profile_counter,
            sku=sku,
            revision=revision,
            board_serial=board_serial,
            seed=seed,
            created_utc=now_utc_iso(),
        )

    def reset_profile(self) -> None:
        self.profile = self._new_profile()
        self._rng = random.Random(self.profile.seed)
        self._generate_components()

    def _generate_components(self) -> None:
        self.components.clear()
        count = self._rng.randint(self.min_components, self.max_components)
        for idx in range(count):
            rect = self._random_component_rect()
            is_def = self._rng.random() < 0.3
            tilt = self._rng.choice([0.0, 5.0, -5.0]) if is_def else 0.0
            self.components.append(
                ComponentSpec(
                    component_id=f"C{idx + 1}",
                    rect=rect,
                    is_defective=is_def,
                    tilt_degrees=tilt,
                )
            )

    def _random_component_rect(self) -> Rect:
        max_attempts = 50
        for _ in range(max_attempts):
            x = self._rng.randint(5, max(5, self.width - self.component_w - 5))
            y = self._rng.randint(5, max(5, self.height - self.component_h - 5))
            cand = Rect(float(x), float(y), float(self.component_w), float(self.component_h))
            if all(not cand.intersects(c.rect) for c in self.components):
                return cand
        # fallback center
        return Rect(
            float(self.width / 2 - self.component_w / 2),
            float(self.height / 2 - self.component_h / 2),
            float(self.component_w),
            float(self.component_h),
        )

    def component_by_id(self, cid: str) -> Optional[ComponentSpec]:
        for c in self.components:
            if c.component_id == cid:
                return c
        return None

    def keepouts(self, *, margin: float = 12.0) -> List[Rect]:
        return [c.rect.inflate(margin) for c in self.components]

    def load_test_case(self, test_case: TestCase) -> None:
        """Load a test case into the world"""
        self.width = test_case.board_width
        self.height = test_case.board_height
        
        # Clear existing components
        self.components.clear()
        
        # Create a mapping of defect details by component ID
        defect_map = {defect.component_id: defect for defect in test_case.defects}
        
        # Load components from test case
        for comp_data in test_case.components:
            rect = Rect(
                float(comp_data["rect"]["x"]),
                float(comp_data["rect"]["y"]),
                float(comp_data["rect"]["w"]),
                float(comp_data["rect"]["h"])
            )
            
            # Get defect details if component is defective
            defect_details = None
            is_defective = comp_data.get("is_defective", False)
            if is_defective and comp_data["component_id"] in defect_map:
                defect = defect_map[comp_data["component_id"]]
                defect_details = {
                    "defect_type": defect.defect_type.value,
                    "severity": defect.severity.value,
                    "description": defect.description,
                    "confidence": defect.confidence,
                    "detection_difficulty": defect.detection_difficulty
                }
            
            component = ComponentSpec(
                component_id=comp_data["component_id"],
                rect=rect,
                is_defective=is_defective,
                tilt_degrees=0.0,  # Can be enhanced later
                defect_details=defect_details
            )
            self.components.append(component)
    
    def get_defects(self) -> List[Dict[str, Any]]:
        """Get all defects in the current world"""
        defects = []
        for component in self.components:
            if component.is_defective and component.defect_details:
                defects.append({
                    "component_id": component.component_id,
                    "location": (component.rect.x, component.rect.y),
                    "size": (component.rect.w, component.rect.h),
                    **component.defect_details
                })
        return defects
    
    def get_test_case_info(self) -> Dict[str, Any]:
        """Get information about the current test case"""
        total_components = len(self.components)
        defective_components = sum(1 for c in self.components if c.is_defective)
        
        defect_types = {}
        defect_severities = {}
        
        for component in self.components:
            if component.is_defective and component.defect_details:
                defect_type = component.defect_details.get("defect_type", "unknown")
                defect_severity = component.defect_details.get("severity", "unknown")
                
                defect_types[defect_type] = defect_types.get(defect_type, 0) + 1
                defect_severities[defect_severity] = defect_severities.get(defect_severity, 0) + 1
        
        return {
            "total_components": total_components,
            "defective_components": defective_components,
            "defect_rate": defective_components / total_components if total_components > 0 else 0.0,
            "defect_types": defect_types,
            "defect_severities": defect_severities,
            "board_size": (self.width, self.height)
        }

