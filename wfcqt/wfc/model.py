"""Core data structures for the wave function collapse solver."""

from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from typing import Dict, Set

from wfcqt.wfc.utilities import EntropyBuckets
@dataclass(frozen=True)
class TileSet:
    """Tile set with adjacency rules and frequencies."""

    tiles: Dict[int, object]
    adjacency: Dict[str, Dict[int, Set[int]]]
    freq: Dict[int, int]
    N: int

class WaveFunction:  # pylint: disable=too-many-instance-attributes
    """State of the wave function grid and propagation logic."""

    DIRS = {"N": (0, -1, "S"), "S": (0, 1, "N"), "W": (-1, 0, "E"), "E": (1, 0, "W")}
    def __init__(self, width: int, height: int, tiles: TileSet, seed: int) -> None:  # pylint: disable=too-many-locals
        """Initialize grid state and adjacency masks."""
        self.width = width
        self.height = height
        self.tiles = tiles

        self._all: Set[int] = set(self.tiles.tiles.keys())
        self.T = len(self.tiles.tiles)
        self._buckets = EntropyBuckets(width * height, self.T)
        self.seed = seed

        self.ALL_MASK = 1 << self.T
        self.ALL_MASK -= 1

        self._poss: list[list[int]] = [[self.ALL_MASK for _ in range(width)] for _ in range(height)]

        for y in range(height):
            for x in range(width):
                idx = y * width + x
                k = self.T
                if k != self._poss[y][x].bit_count():
                    raise ValueError("must be same")
                self._buckets.add(idx, k)


        self.adj_mask = {d: [0] * self.T for d in ("N", "E", "S", "W")}
        for d, mapping in self.tiles.adjacency.items():
            dm = self.adj_mask[d]
            for t, neigh in mapping.items():
                m = 0
                for b in neigh:
                    m |= (1 << b)
                dm[t] = m

        self._buckets.shuffle_buckets(self.seed)

        self.freq = [1] * self.T
        for t, f in self.tiles.freq.items():
            self.freq[t] = max(1, int(f))

        self._rng = random.Random(self.seed)

    def _in_bounds(self, x: int, y: int) -> bool:
        """Return True if coordinates are inside the grid."""
        return 0 <= x < self.width and 0 <= y < self.height


    def observe_next(self) -> tuple[int, int] | None:
        """Select the next lowest-entropy cell index."""
        idx = self._buckets.pop_min()
        if idx is None:
            return None
        return idx % self.width, idx // self.width

    def collapse_cell(self, x: int, y: int) -> None:
        """Collapse the cell at (x, y) using weighted choice."""
        mask = self._poss[y][x]
        assert mask != 0
        if mask.bit_count() == 1:
            self._buckets.remove(y * self.width + x)
            return

        total = 0
        items = []
        for t in self._iter_bits(mask):
            f = self.freq[t]
            items.append((t, f))
            total += f

        r = self._rng.randrange(total)
        acc = 0
        chosen = items[0][0]
        for t, f in items:
            acc += f
            if r < acc:
                chosen = t
                break

        self._poss[y][x] = 1 << chosen
        self._buckets.remove(y * self.width + x)

    @staticmethod
    def _iter_bits(mask: int):
        """Yield set bit indices in ascending order."""
        while mask:
            lsb = mask & -mask
            tid = lsb.bit_length() - 1
            yield tid
            mask ^= lsb

    def propagate(self, x0: int, y0: int) -> bool:  # pylint: disable=too-many-locals
        """Propagate constraints from the given cell."""
        dirs = self.DIRS
        q = deque((x0, y0, d) for d in dirs)

        while q:
            x, y, d = q.popleft()
            dx, dy, inv = dirs[d]
            nx, ny = x + dx, y + dy
            if not (0 <= nx < self.width and 0 <= ny < self.height):
                continue

            A = self._poss[y][x]
            B = self._poss[ny][nx]
            if B == 0:
                return False
            if B.bit_count() <= 1:
                continue

            allowed = 0
            look = self.adj_mask[d]
            for a in self._iter_bits(A):
                allowed |= look[a]

            newB = B & allowed
            if newB == 0:
                return False
            if newB != B:
                self._poss[ny][nx] = newB

                idx = ny * self.width + nx
                self._buckets.move(idx, newB.bit_count())

                for nd, (ddx, ddy, ninv) in dirs.items():
                    _ = ddx, ddy, ninv
                    if nd != inv:
                        q.append((nx, ny, nd))

        return True
