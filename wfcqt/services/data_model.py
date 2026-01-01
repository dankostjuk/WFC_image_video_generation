"""Data model for input images used by the UI."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Dict

import numpy as np

from wfcqt.core.image_loader import ImageLoader

@dataclass(slots=True)
class InputItem:
    """Container for a single input image and metadata."""

    id: str
    name: str
    path: str
    image: np.ndarray
    width: int
    height: int
    channels: int

class InputDataModel:
    """Store input images in memory with unique names."""

    def __init__(self) -> None:
        """Initialize empty input storage."""
        self.data: Dict[str, InputItem] = {}

    def add_from_path(self, path: str, name: str | None = None):
        """Load image from disk and add it under a (unique) name."""
        path = os.path.abspath(path)
        if name is None:
            name = os.path.basename(path)
        if name in self.data:
            raise ValueError(f'Input name already exists: "{name}"')
        img = ImageLoader.load_to_np(path)
        h, w = img.shape[:2]
        c = img.shape[2] if img.ndim == 3 else 1
        item = InputItem(
            id=str(uuid.uuid4()),
            name=name,
            path=path,
            image=img,
            width=w,
            height=h,
            channels=c,
        )
        self.data[name] = item

    def remove(self, name: str) -> None:
        """Remove an item by name if present."""
        if name not in self.data:
            return
        del self.data[name]

    def get(self, name: str) -> InputItem:
        """Return an item by name."""
        return self.data[name]
