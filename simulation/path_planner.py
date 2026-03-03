from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple

import pygame


GridPos = Tuple[int, int]
Point = Tuple[float, float]


@dataclass(frozen=True)
class AStarConfig:
    cell_size: int = 20
    allow_diagonal: bool = True


class AStarPlanner:
    """
    Lightweight A* planner on a 2D occupancy grid in **board-local coordinates**.

    We use it to generate an intuitive "embodied search" behavior:
    - Sweep the board with waypoints
    - When something is detected, plan a path around keepout zones to hover/inspect
    """

    def __init__(self, board_size: Tuple[int, int], *, config: AStarConfig | None = None) -> None:
        self.board_w: int = int(board_size[0])
        self.board_h: int = int(board_size[1])
        self.config: AStarConfig = config or AStarConfig()

    def point_to_cell(self, p: Point) -> GridPos:
        cs = self.config.cell_size
        return (max(0, min(self.grid_w - 1, int(p[0] // cs))), max(0, min(self.grid_h - 1, int(p[1] // cs))))

    def cell_to_point_center(self, c: GridPos) -> Point:
        cs = self.config.cell_size
        return (c[0] * cs + cs / 2.0, c[1] * cs + cs / 2.0)

    @property
    def grid_w(self) -> int:
        return max(1, self.board_w // self.config.cell_size)

    @property
    def grid_h(self) -> int:
        return max(1, self.board_h // self.config.cell_size)

    def build_blocked_cells(self, keepouts_board: Iterable[pygame.Rect]) -> set[GridPos]:
        cs = self.config.cell_size
        blocked: set[GridPos] = set()
        for r in keepouts_board:
            x1 = max(0, int(r.left // cs))
            y1 = max(0, int(r.top // cs))
            x2 = min(self.grid_w - 1, int(r.right // cs))
            y2 = min(self.grid_h - 1, int(r.bottom // cs))
            for gx in range(x1, x2 + 1):
                for gy in range(y1, y2 + 1):
                    blocked.add((gx, gy))
        return blocked

    def plan(
        self,
        start_board: Point,
        goal_board: Point,
        *,
        blocked: set[GridPos],
    ) -> List[Point]:
        start = self.point_to_cell(start_board)
        goal = self.point_to_cell(goal_board)

        if start in blocked:
            blocked = set(blocked)
            blocked.discard(start)
        if goal in blocked:
            blocked = set(blocked)
            blocked.discard(goal)

        came_from: Dict[GridPos, GridPos] = {}
        g_score: Dict[GridPos, float] = {start: 0.0}

        def h(a: GridPos, b: GridPos) -> float:
            # Octile/Manhattan mix depending on diagonal allowance
            dx = abs(a[0] - b[0])
            dy = abs(a[1] - b[1])
            if self.config.allow_diagonal:
                return max(dx, dy)
            return dx + dy

        open_heap: list[tuple[float, GridPos]] = []
        heapq.heappush(open_heap, (h(start, goal), start))
        open_set: set[GridPos] = {start}

        while open_heap:
            _, current = heapq.heappop(open_heap)
            if current not in open_set:
                continue
            open_set.remove(current)

            if current == goal:
                return self._reconstruct_path(came_from, current)

            for nb in self._neighbors(current):
                if nb in blocked:
                    continue
                tentative = g_score[current] + self._step_cost(current, nb)
                if tentative < g_score.get(nb, 1e18):
                    came_from[nb] = current
                    g_score[nb] = tentative
                    f = tentative + h(nb, goal)
                    heapq.heappush(open_heap, (f, nb))
                    open_set.add(nb)

        # No path: return direct-to-goal fallback (still clamped elsewhere).
        return [goal_board]

    def _reconstruct_path(self, came_from: Dict[GridPos, GridPos], end: GridPos) -> List[Point]:
        cells: List[GridPos] = [end]
        cur = end
        while cur in came_from:
            cur = came_from[cur]
            cells.append(cur)
        cells.reverse()
        # Convert to board points centered in each cell
        return [self.cell_to_point_center(c) for c in cells]

    def _neighbors(self, c: GridPos) -> List[GridPos]:
        x, y = c
        nbrs: List[GridPos] = []
        steps = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if self.config.allow_diagonal:
            steps += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        for dx, dy in steps:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.grid_w and 0 <= ny < self.grid_h:
                nbrs.append((nx, ny))
        return nbrs

    def _step_cost(self, a: GridPos, b: GridPos) -> float:
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return 1.4142 if (dx == 1 and dy == 1) else 1.0

