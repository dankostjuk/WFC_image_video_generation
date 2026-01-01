import numpy as np
import pytest
from pathlib import Path
from PIL import Image
from wfcqt.wfc.solver import Solver, Cancelled, Unsolvable
from wfcqt.wfc.analyzer import Analyzer
from wfcqt.wfc.model import TileSet

import hashlib

def hash_image(arr: np.ndarray) -> str:
    # include shape to avoid collisions between different shapes
    h = hashlib.sha256()
    h.update(str(arr.shape).encode("utf-8"))
    h.update(arr.tobytes())
    return h.hexdigest()

class WFCTestConfig():
    def __init__(self):
        self.tile_size: int = 3
        self.output_width: int = 30
        self.output_height: int = 30
        self.periodic_input: bool = True
        self.periodic_output: bool = False
        self.symmetry: int = 1
        self.seed: int = 42
        self.backtrack_limit: int = 1000
        self.show_grid: bool = True

samples_dir = Path(__file__).resolve().parent / "test_samples"
test_img_name = "Town.png"
cfg = WFCTestConfig()
def get_test_tiles():
    analyzer = Analyzer()
    img = Image.open(samples_dir / test_img_name).convert("RGBA")
    img_np =  np.array(img.convert("RGBA"), dtype=np.uint8)
    return analyzer.from_samples([img_np],cfg)


def test_analyzer():
    tiles = list(get_test_tiles().tiles.values())
    paths = sorted((samples_dir / "test_tiles").glob("test_tile*.png"))
    ref = [np.array(Image.open(p).convert("RGBA"), dtype=np.uint8) for p in paths]

    tile_hashes = sorted(hash_image(a) for a in tiles)
    ref_tiles_hashes = sorted(hash_image(a) for a in ref)

    assert tile_hashes == ref_tiles_hashes

def test_solver():
    solver = Solver()
    tiles = get_test_tiles()
    img_np = solver.run(tiles,cfg)
    ref_img = np.array(Image.open(samples_dir / "town_wfc_ref.png").convert("RGBA"), dtype=np.uint8)

    assert np.all(img_np == ref_img)
