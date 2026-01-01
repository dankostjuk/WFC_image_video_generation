"""Image conversion helpers between numpy arrays and Qt images."""
# pylint: disable=no-name-in-module

import numpy as np
from PySide6.QtGui import QImage

def np_to_qimage(arr: np.ndarray) -> QImage:
    """Convert numpy uint8 (H, W, 3|4) to QImage."""
    if arr.dtype != np.uint8:
        raise ValueError("expected uint8 array")
    if arr.ndim != 3 or arr.shape[2] not in (3, 4):
        raise ValueError(f"expected shape (H,W,3|4), got {arr.shape}")

    h, w, c = arr.shape
    fmt = QImage.Format_RGB888 if c == 3 else QImage.Format_RGBA8888
    qimg = QImage(arr.data, w, h, arr.strides[0], fmt)
    return qimg.copy()

def qimage_to_np(qimg: QImage) -> np.ndarray:
    """Convert QImage to numpy uint8 RGBA (H, W, 4)."""
    raise NotImplementedError
