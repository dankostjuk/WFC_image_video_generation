"""Video frame generation and ffmpeg stitching utilities."""
# pylint: disable=no-name-in-module
# pylint: disable=no-member

import os
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed

from PIL import Image, ImageDraw, ImageChops
from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import QWidget


def clamp(x, a, b):
    """Clamp x into [a, b]."""
    return max(a, min(b, x))

def rotate_about_anchor(img: Image.Image, deg: float, anchor_x: float, anchor_y: float) -> Image.Image:
    """Rotate an image about a normalized anchor point."""
    W, H = img.size
    cx = clamp(anchor_x, 0.0, 1.0) * (W - 1)
    cy = clamp(anchor_y, 0.0, 1.0) * (H - 1)
    return img.rotate(deg,resample=Image.NEAREST,expand=False,center=(cx, cy),)


def crop_zoom_and_resize_stable(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    im_big, zoom_factor, target_px, target_py, out_w, out_h, anchor_x, anchor_y
):
    """Crop around an anchor/target and resize back to output size."""
    bigW, bigH = im_big.size
    z = max(1e-9, float(zoom_factor))

    crop_w = max(2, int(bigW / z))
    crop_h = max(2, int(bigH / z))

    crop_w -= (crop_w % 2)
    crop_h -= (crop_h % 2)

    ax = clamp(float(anchor_x), 0.0, 1.0)
    ay = clamp(float(anchor_y), 0.0, 1.0)

    left = int(round(target_px - ax * crop_w))
    top = int(round(target_py - ay * crop_h))

    left = clamp(left, 0, bigW - crop_w)
    top = clamp(top, 0, bigH - crop_h)

    crop = im_big.crop((left, top, left + crop_w, top + crop_h))
    return crop.resize((out_w, out_h), Image.NEAREST)


def paste_at_anchor_point(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    base_img: Image.Image,
    sprite_img: Image.Image,
    anchor_x: float,
    anchor_y: float,
    sprite_target_x: float,
    sprite_target_y: float,
) -> Image.Image:
    """Paste sprite into base image aligned by anchor points."""
    out = base_img.copy().convert("RGBA")
    sprite = sprite_img.convert("RGBA")

    W, H = out.size
    ax = int(round(clamp(anchor_x, 0.0, 1.0) * (W - 1)))
    ay = int(round(clamp(anchor_y, 0.0, 1.0) * (H - 1)))

    tx = int(round(clamp(sprite_target_x, 0.0, 1.0) * (sprite.width - 1)))
    ty = int(round(clamp(sprite_target_y, 0.0, 1.0) * (sprite.height - 1)))

    x = ax - tx
    y = ay - ty

    out.alpha_composite(sprite, (x, y))
    return out


def load_and_superscale(path, bigW, bigH):
    """Load and scale image to the requested size."""
    im = Image.open(path).convert("RGBA")
    return im.resize((bigW, bigH), Image.NEAREST)


def apply_circular_mask(  # pylint: disable=too-many-locals
    img_rgba: Image.Image, cx: int, cy: int, radius: int, feather: int = 0
) -> Image.Image:
    """Apply a circular alpha mask to an RGBA image."""
    img = img_rgba.convert("RGBA")
    W, H = img.size

    mask = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(mask)
    bbox = (cx - radius, cy - radius, cx + radius, cy + radius)
    draw.ellipse(bbox, fill=255)

    if feather > 0:
        small = mask.resize((max(1, W // feather), max(1, H // feather)), Image.BILINEAR)
        mask = small.resize((W, H), Image.BILINEAR)

    r, g, b, a = img.split()
    a2 = ImageChops.multiply(a, mask)  # combine existing alpha with circle
    return Image.merge("RGBA", (r, g, b, a2))


def circular_image(img: Image.Image, cfg: dict):
    """Return a circularly-masked version of the input image."""
    Wf, Hf = img.size
    circle_cx = int(round(cfg["anchor_x"] * (Wf - 1)))
    circle_cy = int(round(cfg["anchor_y"] * (Hf - 1)))
    radius = int(round(min(Wf, Hf) * 0.5))

    return apply_circular_mask(img, circle_cx, circle_cy, radius, feather=0)

def render_one_frame(args):  # pylint: disable=too-many-locals
    """Render a single frame for a given segment."""
    (seg, i, images, cfg_dict, big_w, big_h, zoom_step, denom) = args
    cfg = cfg_dict

    a_big = load_and_superscale(images[seg], big_w, big_h)
    b_big = load_and_superscale(images[seg + 1], big_w, big_h)

    global_frame = seg * cfg["frames_per_segment"] + i
    frame_index = global_frame + 1

    z = cfg["start_zoom"] * (zoom_step ** i)
    rot_deg = global_frame * cfg["rot_deg_per_frame"]

    target_px = int(round(clamp(cfg["target_x"], 0.0, 1.0) * (big_w - 1)))
    target_py = int(round(clamp(cfg["target_y"], 0.0, 1.0) * (big_h - 1)))

    frame_a = crop_zoom_and_resize_stable(
        a_big, z, target_px, target_py, big_w, big_h, cfg["anchor_x"], cfg["anchor_y"]
    ).convert("RGBA")

    if cfg["rot_deg_per_frame"] != 0:
        frame_a = rotate_about_anchor(frame_a, rot_deg, cfg["anchor_x"], cfg["anchor_y"])

    if i < cfg["b_start_frame"]:
        b_scale = 0.0
    elif i >= cfg["b_end_frame"]:
        b_scale = 1.0
    else:
        g = int(i - cfg["b_start_frame"])
        b_scale = ((zoom_step ** g) - 1.0) / denom
        b_scale = float(clamp(b_scale, 0.0, 1.0))

    bw = int(round(big_w * b_scale))
    bh = int(round(big_h * b_scale))

    if bw >= 1 and bh >= 1:
        sprite_b = b_big.resize((bw, bh), Image.NEAREST).convert("RGBA")
        sprite_b = rotate_about_anchor(sprite_b, rot_deg, cfg["target_x"], cfg["target_y"])
        if cfg["circle_input"]:
            sprite_b = circular_image(sprite_b, cfg)

        frame_a = paste_at_anchor_point(
            frame_a, sprite_b, cfg["anchor_x"], cfg["anchor_y"], cfg["target_x"], cfg["target_y"]
        )

    if cfg["circle_input"]:
        frame_a = circular_image(frame_a, cfg)

    out_path = os.path.join(cfg["out_dir"], cfg["name_fmt"] % frame_index)
    frame_a.save(out_path, "PNG", optimize=True)

    return frame_index



class VideoGenerator(QObject):
    """Generate frames and stitch them into a video."""

    progressUpdate = Signal(float)

    def __init__(self, parent: QWidget | None = None):  # pylint: disable=useless-parent-delegation
        """Initialize generator."""
        super().__init__(parent)

    def create_video_from_frames(self, cfg):
        """Run ffmpeg to generate output video files."""
        frames_pattern = os.path.join(cfg.out_dir, cfg.name_fmt)
        for p in ("output_video.mp4", "output_video_reverse.mp4"):
            try:
                os.remove(p)
            except FileNotFoundError:
                pass

        create_video = [
            "ffmpeg",
            "-y",
            "-framerate", str(cfg.fps),
            "-start_number", "1",
            "-i", frames_pattern,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "output_video.mp4",
        ]
        subprocess.run(create_video, check=True)

        self.progressUpdate.emit(0.95)
        if cfg.reverse_output:
            reverse = [
                "ffmpeg",
                "-y",
                "-i", "output_video.mp4",
                "-vf", "reverse",
                "-af", "areverse",
                "output_video_reverse.mp4",
            ]
            subprocess.run(reverse, check=True)

        self.progressUpdate.emit(1.0)

    def run(self, images, cfg, resolution_w=1920, resolution_h=1920):  # pylint: disable=too-many-locals
        """Generate frames in parallel and build a video."""
        images = list(images)
        images.append(images[0])

        os.makedirs(cfg.out_dir, exist_ok=True)
        big_w, big_h = resolution_w, resolution_h

        zoom_step = (cfg.end_zoom / cfg.start_zoom) ** (1.0 / (cfg.frames_per_segment - 1))

        b_end_frame = getattr(cfg, "b_end_frame", cfg.frames_per_segment)

        g_len = max(1, int(b_end_frame - cfg.b_start_frame))
        denom = (zoom_step ** g_len) - 1.0

        total_frames = (len(images) - 1) * cfg.frames_per_segment

        rot_deg_per_frame = 0.0
        if cfg.rotate_input:
            rot_deg_per_frame = 360.0 / (cfg.frames_per_segment * (len(images) - 1))

        cfg_dict = {
            "out_dir": cfg.out_dir,
            "name_fmt": cfg.name_fmt,
            "fps": cfg.fps,
            "frames_per_segment": cfg.frames_per_segment,
            "start_zoom": cfg.start_zoom,
            "end_zoom": cfg.end_zoom,
            "b_start_frame": int(cfg.b_start_frame),
            "b_end_frame": int(b_end_frame),
            "rot_deg_per_frame": float(rot_deg_per_frame),
            "anchor_x": float(cfg.anchor_x),
            "anchor_y": float(cfg.anchor_y),
            "target_x": float(cfg.target_x),
            "target_y": float(cfg.target_y),
            "circle_input": bool(cfg.circle_input),
            "circle_radius_frac": float(cfg.circle_radius_frac),
        }

        tasks = []
        for seg in range(len(images) - 1):
            for i in range(cfg.frames_per_segment):
                tasks.append((seg, i, images, cfg_dict, big_w, big_h, zoom_step, denom))

        done = 0
        max_workers = os.cpu_count() or 4

        with ProcessPoolExecutor(max_workers=max_workers) as ex:
            futures = [ex.submit(render_one_frame, t) for t in tasks]
            for fut in as_completed(futures):
                fut.result()
                done += 1
                self.progressUpdate.emit(done / (total_frames * 1.1))

        self.progressUpdate.emit(0.9)
        self.create_video_from_frames(cfg)
