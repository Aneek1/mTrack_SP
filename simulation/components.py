from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import pygame


Color = Tuple[int, int, int]


@dataclass
class Component:
    """Represents a single PCBA component on the board."""

    component_id: str
    rect: pygame.Rect
    is_defective: bool
    tilt_degrees: float
    base_color: Color

    def draw(self, surface: pygame.Surface) -> None:
        color = self.base_color
        pygame.draw.rect(surface, color, self.rect)
        if self.is_defective:
            # Draw a small red corner marker to make the defect visually obvious.
            marker_size: int = max(4, min(self.rect.width, self.rect.height) // 4)
            marker_rect = pygame.Rect(
                self.rect.right - marker_size,
                self.rect.top,
                marker_size,
                marker_size,
            )
            pygame.draw.rect(surface, (220, 0, 0), marker_rect)

