"""Analyze sample images into tiles and adjacency rules."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from typing import Dict, Iterable, List

import numpy as np

from wfcqt.ui.settings_widget import WFCConfig
from wfcqt.wfc.model import TileSet


class Analyzer:  # pylint: disable=too-few-public-methods
    """Extract tile sets and adjacency from samples."""

    @staticmethod
    def from_samples(samples: List[np.ndarray], cfg: WFCConfig) -> TileSet:
        """Analyze samples into a TileSet."""
        if not samples:
            raise ValueError("from_samples: 'samples' must not be empty.")

        N = cfg.tile_size
        symmetry = cfg.symmetry
        periodic = bool(cfg.periodic_input)

        key_to_id: Dict[bytes, int] = {}
        tiles: Dict[int, np.ndarray] = {}
        freq = Counter()

        all_aug: List[np.ndarray] = []
        for s in samples:
            _validate_sample(s)
            patches = list(_iter_patches(s, N, periodic))
            all_aug.extend(_augment_symmetry(patches, symmetry=symmetry))

        for p in all_aug:
            key = _tile_key(p)
            if key not in key_to_id:
                tid = len(key_to_id)
                key_to_id[key] = tid
                tiles[tid] = p
            freq[key_to_id[key]] += 1

        adjacency = _compute_adjacency(tiles, N)
        return TileSet(tiles=tiles, adjacency=adjacency, freq=dict(freq), N=N)


# ---------- helpers ----------

def _validate_sample(img: np.ndarray) -> None:
    """Validate input sample array shape and dtype."""
    if not isinstance(img, np.ndarray):
        raise TypeError("sample must be a numpy.ndarray")
    if img.ndim != 3 or img.shape[2] not in (3, 4):
        raise ValueError(f"expected image shape (H, W, 3|4), got {img.shape}")
    if img.dtype != np.uint8:
        raise ValueError(f"expected dtype uint8, got {img.dtype}")


def _iter_patches(img: np.ndarray, N: int, periodic: bool) -> Iterable[np.ndarray]:
    """Yield NxN patches from the sample image."""
    H, W, C = img.shape
    _ = C
    y_range = range(H) if periodic else range(H - N + 1)
    x_range = range(W) if periodic else range(W - N + 1)

    for y in y_range:
        for x in x_range:
            if periodic:
                ys = np.arange(y, y + N) % H
                xs = np.arange(x, x + N) % W
                patch = img[np.ix_(ys, xs)]
            else:
                patch = img[y:y + N, x:x + N, :]
            if patch.shape[0] == N and patch.shape[1] == N:
                yield patch


def _augment_symmetry(patches: Iterable[np.ndarray], symmetry: int) -> List[np.ndarray]:
    """Apply symmetry augmentation to patches."""
    if symmetry not in (1, 2, 4, 8):
        symmetry = 1
    out: List[np.ndarray] = []
    for p in patches:
        r0 = p
        r90 = np.rot90(p, 1, axes=(0, 1))
        r180 = np.rot90(p, 2, axes=(0, 1))
        r270 = np.rot90(p, 3, axes=(0, 1))
        variants = [r0, r90, r180, r270]
        if symmetry == 1:
            out.append(r0)
        elif symmetry == 2:
            out.extend([r0, r180])
        elif symmetry == 4:
            out.extend(variants)
        else:  # 8
            for v in variants:
                out.append(np.flip(v, axis=1))  # mirror
            out.extend(variants)
    return out


def _tile_key(patch: np.ndarray) -> bytes:
    """Return a stable tile key for a patch."""
    return hashlib.blake2b(patch.tobytes(), digest_size=16).digest()


def _sig(a: np.ndarray) -> bytes:
    """Stable signature for an array slice."""
    return a.tobytes()  # fast + sufficient; use blake2b(...) if you prefer

def _compute_adjacency(tiles: Dict[int, np.ndarray], N: int) -> Dict[str, Dict[int, set[int]]]:
    """
    Build adjacency for N/E/S/W using (N-1)-pixel overlaps.
    For E/W: match right strip of A to left strip of B.
    For S/N: match bottom strip of A to top strip of B.
    Returns: {dir: {tile_id: set(compatible_ids)}} for dir in {"N","E","S","W"}.
    """
    _ = N
    adj: Dict[str, Dict[int, set[int]]] = {d: defaultdict(set) for d in ("N", "E", "S", "W")}
    ids = list(tiles.keys())

    # Build signature → tile id lists for “incoming” sides
    left_index  = defaultdict(set)  # sig(left strip)  -> {tile ids}
    top_index   = defaultdict(set)  # sig(top strip)   -> {tile ids}

    # Also keep “outgoing” signatures for each tile
    right_sig: Dict[int, bytes] = {}
    bottom_sig: Dict[int, bytes] = {}

    for tid, t in tiles.items():
        # strips are (N x (N-1)) for left/right, ((N-1) x N) for top/bottom
        left_index[_sig(t[:, :-1, :])].add(tid)
        top_index[_sig(t[:-1, :, :])].add(tid)
        right_sig[tid]  = _sig(t[:, 1:,  :])
        bottom_sig[tid] = _sig(t[1:,  :,  :])

    # Now fill adjacency by simple lookups
    for a in ids:
        # East: match A's right strip to others' left strip
        for b in left_index.get(right_sig[a], ()):
            adj["E"][a].add(b)
            adj["W"][b].add(a)

        # South: match A's bottom strip to others' top strip
        for b in top_index.get(bottom_sig[a], ()):
            adj["S"][a].add(b)
            adj["N"][b].add(a)

    # Ensure every tile appears as a key even if no neighbors
    for d in ("N", "E", "S", "W"):
        for tid in ids:
            adj[d].setdefault(tid, set())

    return adj
