"""Solver implementation for wave function collapse."""
# pylint: disable=no-name-in-module

from __future__ import annotations

from threading import Event

import numpy as np
from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import QWidget

from src.ui.settings_widget import WFCConfig
from src.wfc.model import TileSet, WaveFunction



class Unsolvable(Exception):
    """Raised if we fail to find a solution within the restart/backtrack budget."""

class Cancelled(Exception):
    """Raised when a cancellation is requested."""


class Solver(QObject):
    """Run WFC solving with progress updates."""

    on_progress = Signal(np.ndarray)
    def __init__(self, parent: QWidget | None = None):
        """Initialize solver and cancellation flag."""
        super().__init__(parent)
        self._cancel_event = Event()

    def request_cancel(self) -> None:
        """Request cancellation for a running solve."""
        self._cancel_event.set()

    def reset_cancel(self) -> None:
        """Reset cancellation flag."""
        self._cancel_event.clear()

    def run(self, tileset: TileSet, cfg: WFCConfig) -> np.ndarray:  # pylint: disable=too-many-locals
        """Run solver and return the output image."""
        self._cancel_event.clear()
        output_width = cfg.output_width
        output_height = cfg.output_height
        backtrack_limit = cfg.backtrack_limit

        if output_width <= 0 or output_height <= 0:
            raise ValueError("output dimensions must be positive")
        N = tileset.N
        grid_w = max(1, output_width - N + 1)
        grid_h = max(1, output_height - N + 1)


        any_tile = next(iter(tileset.tiles.values()))
        channels = any_tile.shape[2]

        for attempt in range(backtrack_limit):
            _ = attempt
            if self._cancel_event.is_set():
                raise Cancelled()
            wf = WaveFunction(grid_w, grid_h, tileset, cfg.seed)
            while True:
                if self._cancel_event.is_set():
                    raise Cancelled()

                pos = wf.observe_next()
                if pos is None:
                    out = self._render_overlapping(wf, tileset, output_width, output_height, channels)
                    return out

                x, y = pos
                wf.collapse_cell(x, y)

                ok = wf.propagate(x, y)

                self.on_progress.emit(self._render_overlapping(wf, tileset, output_width, output_height, channels))
                if not ok:
                    break

        raise Unsolvable(f"failed after {backtrack_limit} restarts")


    @staticmethod
    def _render_overlapping(  # pylint: disable=too-many-locals
            wf: WaveFunction,
            tileset: TileSet,
            out_w: int,
            out_h: int,
            channels: int,
    ) -> np.ndarray:
        """Render output by overlapping chosen tiles."""
        N = tileset.N
        out = np.zeros((out_h, out_w, channels), dtype=np.uint8)

        grid_h = wf.height
        grid_w = wf.width

        for gy in range(grid_h):
            for gx in range(grid_w):
                mask = wf._poss[gy][gx]  # pylint: disable=protected-access
                if mask == 0:
                    continue

                tid = mask.bit_length() - 1
                tile = tileset.tiles[tid]

                y0 = gy
                x0 = gx
                y1 = min(y0 + N, out_h)
                x1 = min(x0 + N, out_w)

                th = y1 - y0
                tw = x1 - x0
                if th > 0 and tw > 0:
                    out[y0:y1, x0:x1, :] = tile[:th, :tw, :]

        return out
