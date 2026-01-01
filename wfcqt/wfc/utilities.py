"""Utility structures used by the WFC solver."""

from collections import deque
import random
from typing import Optional

class EntropyBuckets:
    """Bucketed entropy tracking for wave function cells."""

    def __init__(self, num_cells: int, num_tiles: int) -> None:
        """Initialize buckets for each entropy level."""
        self.T = int(num_tiles)
        self.N = int(num_cells)
        self.buckets: list[deque[int]] = [deque() for _ in range(self.T + 1)]
        self.where: list[int] = [-1] * self.N
        self.min_k: int = self.T + 1

    def add(self, idx: int, k: int) -> None:
        """Add an index to the bucket for entropy k."""
        if k > 1:
            self.buckets[k].append(idx)
            self.where[idx] = k
            self.min_k = min(self.min_k, k)
        else:
            self.where[idx] = -1

    def move(self, idx: int, new_k: int) -> None:
        """Move an index to a new entropy bucket."""
        old_k = self.where[idx]
        if old_k > 1:
            try:
                self.buckets[old_k].remove(idx)
            except ValueError:
                pass
        self.where[idx] = -1
        self.add(idx, new_k)

    def pop_min(self) -> Optional[int]:
        """Pop the next index from the lowest non-empty bucket."""
        k = self.min_k
        while k <= self.T and not self.buckets[k]:
            k += 1
        if k > self.T:
            self.min_k = self.T + 1
            return None
        self.min_k = k
        idx = self.buckets[k].popleft()
        self.where[idx] = -1
        return idx

    def remove(self, idx: int) -> None:
        """Remove cell idx from its current bucket (if present)."""
        k = self.where[idx]
        if k > 1:
            try:
                self.buckets[k].remove(idx)  # O(n) inside bucket
            except ValueError:
                pass
        self.where[idx] = -1

        if k == self.min_k and k <= self.T and not self.buckets[k]:
            mk = self.min_k + 1
            while mk <= self.T and not self.buckets[mk]:
                mk += 1
            self.min_k = mk

    def shuffle_buckets(self,seed) -> None:
        """Shuffle the minimum-entropy bucket with a deterministic seed."""
        self.min_k = min(self.min_k, self.T + 1)
        random.seed(seed)
        random.shuffle(self.buckets[self.min_k])
