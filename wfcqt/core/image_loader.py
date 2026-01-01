"""Pillow-backed image loading utilities."""

import numpy as np
from PIL import Image, ImageOps


class ImageLoader:
    """Image I/O helpers (Pillow-based in implementation)."""

    @staticmethod
    def load_to_np(path: str) -> np.ndarray:
        """Load an image file to a uint8 ndarray (H, W, 3|4)."""
        try:
            with Image.open(path) as im:
                # Correct orientation from EXIF if present (no-op otherwise)
                im = ImageOps.exif_transpose(im)

                # Normalize to RGB(A)
                if im.mode in ("RGBA", "LA"):
                    im = im.convert("RGBA")
                elif im.mode in ("RGB", "P", "L", "CMYK", "YCbCr", "I;16", "I;16B", "I;16L", "I"):
                    # Convert anything non-RGBA to RGB
                    im = im.convert("RGB")
                else:
                    # Fallback to RGB for any unusual mode
                    im = im.convert("RGB")

                arr = np.array(im, dtype=np.uint8)

                # If RGBA but fully opaque, drop alpha to return 3 channels
                if arr.ndim == 3 and arr.shape[2] == 4:
                    alpha = arr[:, :, 3]
                    if np.all(alpha == 255):
                        arr = arr[:, :, :3]

                # Ensure we return only 3 or 4 channels
                if arr.ndim != 3 or arr.shape[2] not in (3, 4):
                    raise ValueError(f"Unsupported image shape after conversion: {arr.shape}")

                # Detach from PIL memory (np.array already copies, but be explicit)
                return arr.copy()

        except FileNotFoundError:
            raise
        except Exception as e:
            raise ValueError(f"Failed to load image '{path}': {e}") from e

    @staticmethod
    def save_from_np(arr: np.ndarray, path: str) -> None:
        """Save a uint8 ndarray image to disk."""
        raise NotImplementedError
