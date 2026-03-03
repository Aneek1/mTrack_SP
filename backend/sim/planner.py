from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

from .geometry import Rect


GridPos = Tuple[int, int]
Point = Tuple[float, float]


@dataclass(frozen=True)
class AStarConfig:
    cell_size: int = 20
    allow_diagonal: bool = True


class AStarPlanner:
    def __init__(self, board_size: Tuple[int, int], *, config: AStarConfig | None = None) -> None:
        self.board_w: int = int(board_size[0])
        self.board_h: int = int(board_size[1])
        self.config: AStarConfig = config or AStarConfig()

    @property
    def grid_w(self) -> int:
        return max(1, self.board_w // self.config.cell_size)

    @property
    def grid_h(self) -> int:
        return max(1, self.board_h // self.config.cell_size)

    def point_to_cell(self, p: Point) -> GridPos:
        cs = self.config.cell_size
        return (
            max(0, min(self.grid_w - 1, int(p[0] // cs))),
            max(0, min(self.grid_h - 1, int(p[1] // cs))),
        )

    def cell_to_point_center(self, c: GridPos) -> Point:
        cs = self.config.cell_size
        return (c[0] * cs + cs / 2.0, c[1] * cs + cs / 2.0)

    def build_blocked_cells(self, keepouts: Iterable[Rect]) -> set[GridPos]:
        cs = self.config.cell_size
        blocked: set[GridPos] = set()
        for r in keepouts:
            x1 = max(0, int(r.left // cs))
            y1 = max(0, int(r.top // cs))
            x2 = min(self.grid_w - 1, int(r.right // cs))
            y2 = min(self.grid_h - 1, int(r.bottom // cs))
            for gx in range(x1, x2 + 1):
                for gy in range(y1, y2 + 1):
                    blocked.add((gx, gy))
        return blocked

    def plan(self, start: Point, goal: Point, *, blocked: set[GridPos]) -> List[Point]:
        start_c = self.point_to_cell(start)
        goal_c = self.point_to_cell(goal)

        if start_c in blocked:
            blocked = set(blocked)
            blocked.discard(start_c)
        if goal_c in blocked:
            blocked = set(blocked)
            blocked.discard(goal_c)

        came_from: Dict[GridPos, GridPos] = {}
        g_score: Dict[GridPos, float] = {start_c: 0.0}

        def h(a: GridPos, b: GridPos) -> float:
            dx = abs(a[0] - b[0])
            dy = abs(a[1] - b[1])
            return max(dx, dy) if self.config.allow_diagonal else dx + dy

        open_heap: list[tuple[float, GridPos]] = [(h(start_c, goal_c), start_c)]
        open_set: set[GridPos] = {start_c}

        while open_heap:
            _, cur = heapq.heappop(open_heap)
            if cur not in open_set:
                continue
            open_set.remove(cur)

            if cur == goal_c:
                return self._reconstruct(came_from, cur)

            for nb in self._neighbors(cur):
                if nb in blocked:
                    continue
                tentative = g_score[cur] + self._step_cost(cur, nb)
                if tentative < g_score.get(nb, 1e18):
                    came_from[nb] = cur
                    g_score[nb] = tentative
                    heapq.heappush(open_heap, (tentative + h(nb, goal_c), nb))
                    open_set.add(nb)

        return [goal]

    def _reconstruct(self, came_from: Dict[GridPos, GridPos], end: GridPos) -> List[Point]:
        cells: List[GridPos] = [end]
        cur = end
        while cur in came_from:
            cur = came_from[cur]
            cells.append(cur)
        cells.reverse()
        return [self.cell_to_point_center(c) for c in cells]

    def _neighbors(self, c: GridPos) -> List[GridPos]:
        x, y = c
        steps = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if self.config.allow_diagonal:
            steps += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        out: List[GridPos] = []
        for dx, dy in steps:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.grid_w and 0 <= ny < self.grid_h:
                out.append((nx, ny))
        return out

    def _step_cost(self, a: GridPos, b: GridPos) -> float:
        dx = abs(a[0] - b[0])
        dy = abs(a[1] - b[1])
        return 1.4142 if (dx == 1 and dy == 1) else 1.0

