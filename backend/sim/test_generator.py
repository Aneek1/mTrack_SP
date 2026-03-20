"""
Test Case Generator for PCBA Digital Twin Inspection

Generates realistic PCBA boards with configurable defects, component counts,
and difficulty levels for use in the digital twin simulation.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class DefectType(Enum):
    """Types of PCBA defects"""
    MISSING_COMPONENT = "missing_component"
    MISALIGNMENT = "misalignment"
    SOLDER_DEFECT = "solder_defect"
    DAMAGE = "damage"
    CONTAMINATION = "contamination"
    WRONG_COMPONENT = "wrong_component"
    ORIENTATION_ERROR = "orientation_error"
    SIZE_VARIATION = "size_variation"


class DefectSeverity(Enum):
    """Severity levels for defects"""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    COSMETIC = "cosmetic"


@dataclass
class DefectInstance:
    """Represents a single defect on a component"""
    component_id: str
    defect_type: DefectType
    severity: DefectSeverity
    description: str
    confidence: float
    location: Tuple[float, float]
    size: Tuple[float, float]
    detection_difficulty: float  # 0.0 (easy) to 1.0 (hard)


@dataclass
class TestCase:
    """Represents a complete test case for PCBA inspection"""
    test_id: str
    name: str
    description: str
    board_width: int
    board_height: int
    components: List[Dict[str, Any]]
    defects: List[DefectInstance]
    defect_rate: float
    difficulty_level: str
    estimated_inspection_time: float
    created_utc: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# Defect descriptions for generating realistic test scenarios
_DEFECT_DESCRIPTIONS: Dict[DefectType, List[str]] = {
    DefectType.MISSING_COMPONENT: [
        "Component pad is empty — no component placed",
        "Component completely absent from designated position",
        "Missing chip at expected mounting location",
    ],
    DefectType.MISALIGNMENT: [
        "Component shifted 1.2 mm left of center pad",
        "Rotational misalignment of ~15 degrees",
        "Component offset from solder pads",
    ],
    DefectType.SOLDER_DEFECT: [
        "Cold solder joint detected on pin 3",
        "Solder bridge between adjacent pins",
        "Insufficient solder on pad — dry joint",
    ],
    DefectType.DAMAGE: [
        "Cracked component body visible under inspection",
        "Chipped corner on IC package",
        "Burn mark on component surface",
    ],
    DefectType.CONTAMINATION: [
        "Flux residue around component leads",
        "Foreign particle on solder joint",
        "Corrosion visible on component terminals",
    ],
    DefectType.WRONG_COMPONENT: [
        "10kΩ resistor placed where 4.7kΩ expected",
        "Wrong package size — 0603 instead of 0402",
        "Incorrect IC variant installed",
    ],
    DefectType.ORIENTATION_ERROR: [
        "Polarised capacitor installed in reverse",
        "IC pin-1 marker rotated 180 degrees",
        "Diode cathode marking reversed",
    ],
    DefectType.SIZE_VARIATION: [
        "Component body 0.3 mm oversized",
        "Lead length exceeds specification by 0.5 mm",
        "Pad coverage less than 75 % — undersized component",
    ],
}

_SEVERITY_WEIGHTS: Dict[str, Dict[DefectSeverity, float]] = {
    "easy": {
        DefectSeverity.CRITICAL: 0.4,
        DefectSeverity.MAJOR: 0.35,
        DefectSeverity.MINOR: 0.15,
        DefectSeverity.COSMETIC: 0.1,
    },
    "medium": {
        DefectSeverity.CRITICAL: 0.2,
        DefectSeverity.MAJOR: 0.3,
        DefectSeverity.MINOR: 0.3,
        DefectSeverity.COSMETIC: 0.2,
    },
    "hard": {
        DefectSeverity.CRITICAL: 0.1,
        DefectSeverity.MAJOR: 0.2,
        DefectSeverity.MINOR: 0.35,
        DefectSeverity.COSMETIC: 0.35,
    },
}

_DIFFICULTY_DETECTION: Dict[str, Tuple[float, float]] = {
    "easy": (0.0, 0.3),
    "medium": (0.25, 0.65),
    "hard": (0.5, 1.0),
}

# Component type templates
_COMPONENT_TYPES: List[Dict[str, Any]] = [
    {"label": "resistor", "min_w": 20, "max_w": 50, "min_h": 10, "max_h": 25},
    {"label": "capacitor", "min_w": 20, "max_w": 45, "min_h": 12, "max_h": 30},
    {"label": "IC", "min_w": 40, "max_w": 80, "min_h": 30, "max_h": 60},
    {"label": "connector", "min_w": 50, "max_w": 100, "min_h": 15, "max_h": 35},
    {"label": "inductor", "min_w": 25, "max_w": 50, "min_h": 20, "max_h": 40},
    {"label": "diode", "min_w": 15, "max_w": 35, "min_h": 10, "max_h": 20},
    {"label": "transistor", "min_w": 20, "max_w": 40, "min_h": 15, "max_h": 30},
    {"label": "LED", "min_w": 15, "max_w": 30, "min_h": 12, "max_h": 25},
]


class TestCaseGenerator:
    """Generates random PCBA test cases with configurable parameters."""

    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)

    # ---- public API ----

    def generate_test_case(
        self,
        *,
        board_width: int = 840,
        board_height: int = 520,
        num_components: Optional[int] = None,
        defect_rate: Optional[float] = None,
        difficulty_level: str = "medium",
    ) -> TestCase:
        """Generate a random test case."""
        difficulty_level = difficulty_level.lower()
        if difficulty_level not in ("easy", "medium", "hard"):
            difficulty_level = "medium"

        if num_components is None:
            num_components = self._rng.randint(5, 50)
        num_components = max(5, min(50, num_components))

        if defect_rate is None:
            defect_rate = {
                "easy": self._rng.uniform(0.2, 0.4),
                "medium": self._rng.uniform(0.15, 0.35),
                "hard": self._rng.uniform(0.1, 0.25),
            }[difficulty_level]
        defect_rate = max(0.0, min(1.0, defect_rate))

        # Place components
        components = self._place_components(
            board_width, board_height, num_components
        )

        # Generate defects
        num_defects = max(1, int(num_components * defect_rate))
        defect_indices = self._rng.sample(
            range(num_components), min(num_defects, num_components)
        )
        defects: List[DefectInstance] = []
        for idx in defect_indices:
            comp = components[idx]
            comp["is_defective"] = True
            defect = self._generate_defect(comp, difficulty_level)
            defects.append(defect)

        test_id = f"TC-{uuid.uuid4().hex[:8].upper()}"
        estimated_time = num_components * 1.5  # rough seconds per component

        return TestCase(
            test_id=test_id,
            name=f"PCBA Inspection — {num_components} components, {difficulty_level}",
            description=(
                f"Auto-generated test with {num_components} components, "
                f"{len(defects)} seeded defects ({defect_rate:.0%} rate), "
                f"difficulty={difficulty_level}"
            ),
            board_width=board_width,
            board_height=board_height,
            components=components,
            defects=defects,
            defect_rate=defect_rate,
            difficulty_level=difficulty_level,
            estimated_inspection_time=estimated_time,
        )

    def serialize_test_case(self, tc: TestCase) -> Dict[str, Any]:
        """Serialize a TestCase to a plain dict for JSON transport."""
        return {
            "test_id": tc.test_id,
            "name": tc.name,
            "description": tc.description,
            "board_width": tc.board_width,
            "board_height": tc.board_height,
            "components": tc.components,
            "defects": [
                {
                    "component_id": d.component_id,
                    "defect_type": d.defect_type.value,
                    "severity": d.severity.value,
                    "description": d.description,
                    "confidence": d.confidence,
                    "location": list(d.location),
                    "size": list(d.size),
                    "detection_difficulty": d.detection_difficulty,
                }
                for d in tc.defects
            ],
            "defect_rate": tc.defect_rate,
            "difficulty_level": tc.difficulty_level,
            "estimated_inspection_time": tc.estimated_inspection_time,
            "created_utc": tc.created_utc,
        }

    def deserialize_test_case(self, data: Dict[str, Any]) -> TestCase:
        """Deserialize a dict back into a TestCase."""
        defects = [
            DefectInstance(
                component_id=d["component_id"],
                defect_type=DefectType(d["defect_type"]),
                severity=DefectSeverity(d["severity"]),
                description=d["description"],
                confidence=d["confidence"],
                location=tuple(d["location"]),
                size=tuple(d["size"]),
                detection_difficulty=d["detection_difficulty"],
            )
            for d in data.get("defects", [])
        ]
        return TestCase(
            test_id=data["test_id"],
            name=data["name"],
            description=data["description"],
            board_width=data["board_width"],
            board_height=data["board_height"],
            components=data["components"],
            defects=defects,
            defect_rate=data["defect_rate"],
            difficulty_level=data["difficulty_level"],
            estimated_inspection_time=data.get("estimated_inspection_time", 0.0),
            created_utc=data.get(
                "created_utc", datetime.now(timezone.utc).isoformat()
            ),
        )

    # ---- internal helpers ----

    def _place_components(
        self, board_w: int, board_h: int, count: int
    ) -> List[Dict[str, Any]]:
        """Place *count* non-overlapping components on the board."""
        placed: List[Dict[str, Any]] = []
        margin = 10

        for idx in range(count):
            tmpl = self._rng.choice(_COMPONENT_TYPES)
            w = self._rng.randint(tmpl["min_w"], tmpl["max_w"])
            h = self._rng.randint(tmpl["min_h"], tmpl["max_h"])

            rect = self._find_free_position(board_w, board_h, w, h, placed, margin)
            placed.append(
                {
                    "component_id": f"C{idx + 1}",
                    "label": tmpl["label"],
                    "rect": {"x": rect[0], "y": rect[1], "w": rect[2], "h": rect[3]},
                    "is_defective": False,
                }
            )
        return placed

    def _find_free_position(
        self,
        board_w: int,
        board_h: int,
        w: int,
        h: int,
        existing: List[Dict[str, Any]],
        margin: int,
    ) -> Tuple[float, float, float, float]:
        """Return (x, y, w, h) for a non-overlapping placement."""
        for _ in range(200):
            x = self._rng.randint(margin, max(margin, board_w - w - margin))
            y = self._rng.randint(margin, max(margin, board_h - h - margin))
            candidate = (x, y, w, h)
            if all(not self._rects_overlap(candidate, e) for e in existing):
                return (float(x), float(y), float(w), float(h))
        # fallback — centre of board
        return (
            float(board_w // 2 - w // 2),
            float(board_h // 2 - h // 2),
            float(w),
            float(h),
        )

    @staticmethod
    def _rects_overlap(
        cand: Tuple[float, float, float, float], comp: Dict[str, Any]
    ) -> bool:
        r = comp["rect"]
        cx, cy, cw, ch = cand
        rx, ry, rw, rh = r["x"], r["y"], r["w"], r["h"]
        pad = 5
        return not (
            cx + cw + pad < rx
            or rx + rw + pad < cx
            or cy + ch + pad < ry
            or ry + rh + pad < cy
        )

    def _generate_defect(
        self, comp: Dict[str, Any], difficulty: str
    ) -> DefectInstance:
        defect_type = self._rng.choice(list(DefectType))
        severity = self._pick_severity(difficulty)
        lo, hi = _DIFFICULTY_DETECTION.get(difficulty, (0.2, 0.6))
        detection_difficulty = self._rng.uniform(lo, hi)
        confidence = self._rng.uniform(0.7, 1.0)

        descriptions = _DEFECT_DESCRIPTIONS.get(defect_type, ["Unknown defect"])
        description = self._rng.choice(descriptions)

        rect = comp["rect"]
        location = (rect["x"] + rect["w"] / 2.0, rect["y"] + rect["h"] / 2.0)
        size = (rect["w"], rect["h"])

        return DefectInstance(
            component_id=comp["component_id"],
            defect_type=defect_type,
            severity=severity,
            description=description,
            confidence=confidence,
            location=location,
            size=size,
            detection_difficulty=detection_difficulty,
        )

    def _pick_severity(self, difficulty: str) -> DefectSeverity:
        weights = _SEVERITY_WEIGHTS.get(difficulty, _SEVERITY_WEIGHTS["medium"])
        severities = list(weights.keys())
        probs = [weights[s] for s in severities]
        return self._rng.choices(severities, weights=probs, k=1)[0]
