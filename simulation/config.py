from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WindowConfig:
    width: int = 960
    height: int = 640
    title: str = "High-Mix Visual Inspection Agent (mTrac Simulation)"
    fps: int = 60


@dataclass(frozen=True)
class BoardConfig:
    margin: int = 60
    background_color: tuple[int, int, int] = (10, 60, 10)
    border_color: tuple[int, int, int] = (0, 200, 0)


@dataclass(frozen=True)
class ComponentConfig:
    min_count: int = 5
    max_count: int = 10
    width: int = 60
    height: int = 30
    color_ok: tuple[int, int, int] = (180, 180, 180)
    color_defective: tuple[int, int, int] = (220, 80, 80)


@dataclass(frozen=True)
class GantryConfig:
    size: int = 40
    color: tuple[int, int, int] = (80, 160, 255)
    home_position: tuple[float, float] = (0.0, 0.0)
    speed_pixels_per_second: float = 200.0


@dataclass(frozen=True)
class ControlConfig:
    manual_speed_pixels_per_second: float = 260.0
    ai_replan_hz: float = 2.0


@dataclass(frozen=True)
class CameraConfig:
    # Camera field-of-view size in pixels (and board units for this sim)
    fov_width: int = 320
    fov_height: int = 240


@dataclass(frozen=True)
class AIConfig:
    # Simulated API failure rate for the placeholder LLM call.
    # Set to 0.0 to avoid confusing SAFE_RETURN behavior while learning.
    simulated_api_failure_rate: float = 0.0


@dataclass(frozen=True)
class UIConfig:
    button_width: int = 220
    button_height: int = 40
    button_margin: int = 15
    button_color: tuple[int, int, int] = (40, 40, 120)
    button_hover_color: tuple[int, int, int] = (70, 70, 170)
    button_text_color: tuple[int, int, int] = (255, 255, 255)
    font_size: int = 18
    button_label: str = "Change Product Profile"
    # Split-screen digital twin UI
    side_panel_width: int = 360
    side_panel_gap: int = 20
    side_panel_padding: int = 12
    side_panel_bg: tuple[int, int, int] = (15, 15, 18)
    side_panel_border: tuple[int, int, int] = (80, 80, 90)


WINDOW_CONFIG = WindowConfig()
BOARD_CONFIG = BoardConfig()
COMPONENT_CONFIG = ComponentConfig()
GANTRY_CONFIG = GantryConfig()
CONTROL_CONFIG = ControlConfig()
CAMERA_CONFIG = CameraConfig()
AI_CONFIG = AIConfig()
UI_CONFIG = UIConfig()

