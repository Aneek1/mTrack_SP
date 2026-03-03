from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Tuple

import pygame

from .components import Component
from .config import BOARD_CONFIG, COMPONENT_CONFIG, UI_CONFIG, WINDOW_CONFIG
from .product_profile import ProductProfile
from .perception_types import CameraPatch, Detection


@dataclass(frozen=True)
class BoardGeometry:
    width: int
    height: int


class PCBAEnvironment:
    """2D top-down PCBA board with randomly placed components."""

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen: pygame.Surface = screen
        self.board_rect: pygame.Rect = self._create_board_rect()
        self.side_panel_rect: pygame.Rect = self._create_side_panel_rect()
        self.components: List[Component] = []
        self.font: pygame.font.Font = pygame.font.SysFont(
            "Arial", UI_CONFIG.font_size
        )
        self.button_rect: pygame.Rect = self._create_button_rect()
        self._profile_counter: int = 0
        self.profile: ProductProfile = self._new_profile()
        self._rng: random.Random = random.Random(self.profile.seed)
        self._generate_components()
        self._board_render_cache: pygame.Surface | None = None
        self._board_render_cache_profile_id: int | None = None

    def _create_board_rect(self) -> pygame.Rect:
        margin: int = BOARD_CONFIG.margin
        width: int = (
            WINDOW_CONFIG.width
            - 2 * margin
            - UI_CONFIG.side_panel_width
            - UI_CONFIG.side_panel_gap
        )
        height: int = WINDOW_CONFIG.height - 2 * margin - (UI_CONFIG.button_height + UI_CONFIG.button_margin)
        return pygame.Rect(margin, margin + UI_CONFIG.button_height + UI_CONFIG.button_margin, width, height)

    def _create_side_panel_rect(self) -> pygame.Rect:
        margin: int = BOARD_CONFIG.margin
        x: int = WINDOW_CONFIG.width - margin - UI_CONFIG.side_panel_width
        y: int = UI_CONFIG.button_margin
        height: int = WINDOW_CONFIG.height - y - margin
        return pygame.Rect(x, y, UI_CONFIG.side_panel_width, height)

    def _create_button_rect(self) -> pygame.Rect:
        x: int = BOARD_CONFIG.margin
        y: int = UI_CONFIG.button_margin
        return pygame.Rect(
            x,
            y,
            UI_CONFIG.button_width,
            UI_CONFIG.button_height,
        )

    def _new_profile(self) -> ProductProfile:
        self._profile_counter += 1
        seed: int = random.randint(1, 2_147_483_647)
        sku: str = f"SKU-{random.randint(100, 999)}"
        revision: str = random.choice(["A", "B", "C"])
        board_serial: str = f"BOARD-{self._profile_counter:04d}"
        return ProductProfile(
            profile_id=self._profile_counter,
            sku=sku,
            revision=revision,
            board_serial=board_serial,
            seed=seed,
            created_utc=ProductProfile.now_utc_iso(),
        )

    def _generate_components(self) -> None:
        self.components.clear()
        self._invalidate_board_render_cache()
        count: int = self._rng.randint(
            COMPONENT_CONFIG.min_count, COMPONENT_CONFIG.max_count
        )

        for index in range(count):
            rect = self._random_component_rect()
            is_defective: bool = self._rng.random() < 0.3
            base_color = (
                COMPONENT_CONFIG.color_defective
                if is_defective
                else COMPONENT_CONFIG.color_ok
            )
            tilt_degrees: float = (
                self._rng.choice([0.0, 5.0, -5.0]) if is_defective else 0.0
            )
            component = Component(
                component_id=f"C{index + 1}",
                rect=rect,
                is_defective=is_defective,
                tilt_degrees=tilt_degrees,
                base_color=base_color,
            )
            self.components.append(component)

    def _random_component_rect(self) -> pygame.Rect:
        max_attempts: int = 50
        for _ in range(max_attempts):
            x: int = self._rng.randint(
                self.board_rect.left + 5,
                self.board_rect.right - COMPONENT_CONFIG.width - 5,
            )
            y: int = self._rng.randint(
                self.board_rect.top + 5,
                self.board_rect.bottom - COMPONENT_CONFIG.height - 5,
            )
            candidate = pygame.Rect(
                x,
                y,
                COMPONENT_CONFIG.width,
                COMPONENT_CONFIG.height,
            )
            if not any(candidate.colliderect(c.rect) for c in self.components):
                return candidate

        # Fallback: return something in the center if packing is difficult.
        return pygame.Rect(
            (self.board_rect.centerx - COMPONENT_CONFIG.width // 2),
            (self.board_rect.centery - COMPONENT_CONFIG.height // 2),
            COMPONENT_CONFIG.width,
            COMPONENT_CONFIG.height,
        )

    def reset_board(self) -> None:
        """High-mix mode: reshuffle all components."""
        self.profile = self._new_profile()
        self._rng = random.Random(self.profile.seed)
        self._generate_components()

    def draw(
        self,
        gantry_rect: pygame.Rect,
        overlay_lines: List[str] | None = None,
        *,
        camera_patch: CameraPatch | None = None,
        detections: List[Detection] | None = None,
        inspection_results: dict[str, str] | None = None,
    ) -> None:
        self._draw_background()
        self._draw_board()
        self._draw_components()
        if inspection_results:
            self._draw_inspection_results(inspection_results)
        if detections:
            self._draw_detections(detections)
        self._draw_gantry(gantry_rect)
        self._draw_high_mix_button()
        self._draw_side_panel(lines=overlay_lines or [], camera_patch=camera_patch)

    def _draw_background(self) -> None:
        self.screen.fill((20, 20, 20))

    def _draw_board(self) -> None:
        pygame.draw.rect(
            self.screen,
            BOARD_CONFIG.background_color,
            self.board_rect,
        )
        pygame.draw.rect(
            self.screen,
            BOARD_CONFIG.border_color,
            self.board_rect,
            width=2,
        )

    def _draw_components(self) -> None:
        for component in self.components:
            component.draw(self.screen)

    def _draw_inspection_results(self, results: dict[str, str]) -> None:
        # Draw PASS/FAIL only for components that have been inspected.
        for c in self.components:
            if c.component_id not in results:
                continue
            status = results[c.component_id]
            color = (40, 220, 80) if status == "PASS" else (240, 70, 70)
            pygame.draw.rect(self.screen, color, c.rect, width=3)
            label = self.font.render(f"{c.component_id}:{status}", True, color)
            self.screen.blit(label, (c.rect.left, max(self.board_rect.top, c.rect.top - UI_CONFIG.font_size - 2)))

    def _draw_detections(self, detections: List[Detection]) -> None:
        for det in detections:
            x1, y1, x2, y2 = det.bbox_board_xyxy
            sx1, sy1 = self.board_to_screen((x1, y1))
            sx2, sy2 = self.board_to_screen((x2, y2))
            rect = pygame.Rect(int(sx1), int(sy1), int(sx2 - sx1), int(sy2 - sy1))
            color = (255, 220, 50) if det.source == "yolo" else (60, 200, 255)
            pygame.draw.rect(self.screen, color, rect, width=2)
            label = f"{det.label} {det.confidence:.2f}"
            if det.component_id:
                label = f"{det.component_id}:{label}"
            surf = self.font.render(label, True, color)
            self.screen.blit(surf, (rect.left, max(self.board_rect.top, rect.top - UI_CONFIG.font_size - 2)))

    def _draw_gantry(self, gantry_rect: pygame.Rect) -> None:
        pygame.draw.rect(self.screen, (80, 160, 255), gantry_rect, width=2)

    def _draw_high_mix_button(self) -> None:
        mouse_pos: Tuple[int, int] = pygame.mouse.get_pos()
        is_hovered: bool = self.button_rect.collidepoint(mouse_pos)
        color = (
            UI_CONFIG.button_hover_color if is_hovered else UI_CONFIG.button_color
        )
        pygame.draw.rect(self.screen, color, self.button_rect, border_radius=4)

        label_surface = self.font.render(
            UI_CONFIG.button_label,
            True,
            UI_CONFIG.button_text_color,
        )
        label_rect = label_surface.get_rect(center=self.button_rect.center)
        self.screen.blit(label_surface, label_rect)

    def _draw_side_panel(self, *, lines: List[str], camera_patch: CameraPatch | None) -> None:
        rect = self.side_panel_rect
        pygame.draw.rect(self.screen, UI_CONFIG.side_panel_bg, rect)
        pygame.draw.rect(self.screen, UI_CONFIG.side_panel_border, rect, width=1)

        pad: int = UI_CONFIG.side_panel_padding
        x: int = rect.left + pad
        y: int = rect.top + pad
        max_w: int = rect.width - 2 * pad

        # Camera view at top of panel
        if camera_patch is not None:
            cam_w: int = max_w
            cam_h: int = int(cam_w * (camera_patch.size[1] / max(1.0, float(camera_patch.size[0]))))
            cam_h = min(cam_h, 200)
            cam_rect = pygame.Rect(x, y, cam_w, cam_h)
            pygame.draw.rect(self.screen, (30, 30, 30), cam_rect)
            pygame.draw.rect(self.screen, (200, 200, 200), cam_rect, width=1)
            scaled = pygame.transform.smoothscale(camera_patch.surface, (cam_w, cam_h))
            self.screen.blit(scaled, (x, y))
            title = self.font.render("Perception: Camera FOV", True, (240, 240, 240))
            self.screen.blit(title, (x + 6, y + 6))
            y += cam_h + 10

        # Text log with wrapping
        header = self.font.render("Thought Log", True, (240, 240, 240))
        self.screen.blit(header, (x, y))
        y += UI_CONFIG.font_size + 6

        for line in lines:
            for wrapped in self._wrap_text(line, max_w):
                if y > rect.bottom - pad - UI_CONFIG.font_size:
                    more = self.font.render("... (more)", True, (200, 200, 200))
                    self.screen.blit(more, (x, rect.bottom - pad - UI_CONFIG.font_size))
                    return
                surf = self.font.render(wrapped, True, (230, 230, 230))
                self.screen.blit(surf, (x, y))
                y += UI_CONFIG.font_size + 2
            y += 2

    def _wrap_text(self, text: str, max_width: int) -> List[str]:
        # Basic word-wrap using pixel measurement.
        if not text:
            return [""]
        words = text.split(" ")
        lines: List[str] = []
        cur = ""
        for w in words:
            candidate = w if not cur else f"{cur} {w}"
            if self.font.size(candidate)[0] <= max_width:
                cur = candidate
            else:
                if cur:
                    lines.append(cur)
                # If a single word is too long, hard-split it.
                if self.font.size(w)[0] <= max_width:
                    cur = w
                else:
                    chunk = ""
                    for ch in w:
                        cand2 = chunk + ch
                        if self.font.size(cand2)[0] <= max_width:
                            chunk = cand2
                        else:
                            if chunk:
                                lines.append(chunk)
                            chunk = ch
                    cur = chunk
        if cur:
            lines.append(cur)
        return lines

    def handle_mouse_click(self, position: Tuple[int, int]) -> bool:
        """Handle a mouse click; returns True if high-mix button was activated."""
        if self.button_rect.collidepoint(position):
            self.reset_board()
            return True
        return False

    def get_components_under_gantry(
        self,
        gantry_rect: pygame.Rect,
    ) -> List[Component]:
        return [c for c in self.components if c.rect.colliderect(gantry_rect)]

    def get_components_in_board_rect(self, board_rect: pygame.Rect) -> List[Component]:
        """Return components whose board-local rect intersects board_rect."""
        out: List[Component] = []
        for c in self.components:
            rect_board = self.component_rect_to_board(c.rect)
            if rect_board.colliderect(board_rect):
                out.append(c)
        return out

    def get_keepout_rects_board(self, *, margin: int = 10) -> List[pygame.Rect]:
        """Rects in board coords that the gantry should avoid (for A*)."""
        keepouts: List[pygame.Rect] = []
        for c in self.components:
            r = self.component_rect_to_board(c.rect)
            keepouts.append(
                pygame.Rect(
                    r.left - margin,
                    r.top - margin,
                    r.width + 2 * margin,
                    r.height + 2 * margin,
                )
            )
        return keepouts

    def get_component_by_id(self, component_id: str) -> Component | None:
        for c in self.components:
            if c.component_id == component_id:
                return c
        return None

    def get_board_geometry(self) -> BoardGeometry:
        return BoardGeometry(width=self.board_rect.width, height=self.board_rect.height)

    def board_to_screen(self, board_xy: Tuple[float, float]) -> Tuple[float, float]:
        """Convert board-local coordinates to screen coordinates."""
        return (
            self.board_rect.left + board_xy[0],
            self.board_rect.top + board_xy[1],
        )

    def screen_to_board(self, screen_xy: Tuple[float, float]) -> Tuple[float, float]:
        """Convert screen coordinates to board-local coordinates."""
        return (
            screen_xy[0] - self.board_rect.left,
            screen_xy[1] - self.board_rect.top,
        )

    def is_point_on_board(self, screen_xy: Tuple[int, int]) -> bool:
        return self.board_rect.collidepoint(screen_xy)

    def component_rect_to_board(self, component_rect_screen: pygame.Rect) -> pygame.Rect:
        """Convert a component rect from screen space into board-local coordinates."""
        return pygame.Rect(
            component_rect_screen.left - self.board_rect.left,
            component_rect_screen.top - self.board_rect.top,
            component_rect_screen.width,
            component_rect_screen.height,
        )

    def render_board_surface(self) -> pygame.Surface:
        """
        Render the board into an offscreen surface in board-local coordinates.

        This surface is the "ground truth image" that the virtual camera crops from.
        """
        if self._board_render_cache is not None and self._board_render_cache_profile_id == self.profile.profile_id:
            return self._board_render_cache

        geom = self.get_board_geometry()
        surf = pygame.Surface((geom.width, geom.height))
        surf.fill(BOARD_CONFIG.background_color)

        for component in self.components:
            rect_board = self.component_rect_to_board(component.rect)
            # Draw body
            pygame.draw.rect(surf, component.base_color, rect_board)
            # Defect marker
            if component.is_defective:
                marker_size: int = max(4, min(rect_board.width, rect_board.height) // 4)
                marker_rect = pygame.Rect(
                    rect_board.right - marker_size,
                    rect_board.top,
                    marker_size,
                    marker_size,
                )
                pygame.draw.rect(surf, (220, 0, 0), marker_rect)

        self._board_render_cache = surf
        self._board_render_cache_profile_id = self.profile.profile_id
        return surf

    def render_camera_patch(
        self,
        gantry_center_board_xy: Tuple[float, float],
        size: Tuple[int, int],
    ) -> CameraPatch:
        """
        Crop a camera patch (FOV) centered at gantry_center_board_xy.

        Returns:
        - patch surface
        - patch origin (top-left) in board coordinates
        """
        board = self.render_board_surface()
        board_w, board_h = board.get_size()
        patch_w, patch_h = size

        cx, cy = gantry_center_board_xy
        x0 = float(cx) - patch_w / 2.0
        y0 = float(cy) - patch_h / 2.0

        # Clamp origin to board bounds.
        x0 = max(0.0, min(float(board_w - patch_w), x0))
        y0 = max(0.0, min(float(board_h - patch_h), y0))

        src_rect = pygame.Rect(int(x0), int(y0), int(patch_w), int(patch_h))
        patch_surf = pygame.Surface((patch_w, patch_h))
        patch_surf.blit(board, (0, 0), area=src_rect)
        return CameraPatch(surface=patch_surf, origin_board_xy=(x0, y0), size=(patch_w, patch_h))

    def _invalidate_board_render_cache(self) -> None:
        self._board_render_cache = None
        self._board_render_cache_profile_id = None

