import numpy as np
from PIL import Image

from wfcqt.wfc.video_generation import  render_one_frame

def make_rgba(w=8, h=8, color=(0, 0, 0, 0)):
    return Image.new("RGBA", (w, h), color)


def test_render_one_frame(tmp_path):
    a_path = tmp_path / "a.png"
    b_path = tmp_path / "b.png"
    make_rgba(10, 10, (255, 0, 0, 255)).save(a_path)
    make_rgba(10, 10, (0, 255, 0, 255)).save(b_path)

    out_dir = tmp_path / "frames"
    out_dir.mkdir()

    cfg = {
        "out_dir": str(out_dir),
        "name_fmt": "frame_%06d.png",
        "frames_per_segment": 5,
        "start_zoom": 1.0,
        "end_zoom": 2.0,
        "b_start_frame": 1,
        "b_end_frame": 5,
        "rot_deg_per_frame": 0.0,
        "anchor_x": 0.5,
        "anchor_y": 0.5,
        "target_x": 0.5,
        "target_y": 0.5,
        "circle_input": False,
        "circle_radius_frac": 0.5,
    }

    seg = 0
    i = 2
    big_w = 64
    big_h = 64
    zoom_step = 1.01
    denom = 1.0

    first_appear_frame = render_one_frame((seg, i, [str(a_path), str(b_path)], cfg, big_w, big_h, zoom_step, denom))
    expected = out_dir / ("frame_%06d.png" % first_appear_frame)
    assert expected.exists()
    img = Image.open(expected).convert("RGBA")
    assert np.array_equal(np.array(img.convert("RGBA"), dtype=np.uint8)[big_w//2,big_h//2,:],np.array([0,255,0,255]))
    i = cfg["b_end_frame"]
    last_appear_frame = render_one_frame((seg, i, [str(a_path), str(b_path)], cfg, big_w, big_h, zoom_step, denom))
    expected = out_dir / ("frame_%06d.png" % last_appear_frame)

    assert expected.exists()
    img = Image.open(expected).convert("RGBA")
    assert np.array_equal(np.array(img.convert("RGBA"), dtype=np.uint8)[big_w // 2, big_h // 2, :],np.array([0, 255, 0, 255]))
    assert np.array_equal(np.array(img.convert("RGBA"), dtype=np.uint8)[0, 0, :],np.array([0, 255, 0, 255]))

    Image.open(expected).load()
