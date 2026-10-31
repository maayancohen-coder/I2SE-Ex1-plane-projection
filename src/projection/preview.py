"""Helpers of the GUI that do not need a window, so they can be tested anywhere."""
import math
from pathlib import Path

import numpy as np

from projection.plane import Trapezoid, Triangle
from projection.video_writer import ERROR_FRAME_SIZE, ErrorFrame

PREVIEW_BOX = (360, 360)        # (height, width) of the preview area in the window
MAX_TILT = 60                   # degrees, for the explore sliders

# For each "cut across" axis: which volume axis is the base direction (u), the apex-to-base
# direction (v) and the axis the plane moves along (w).
AXES = {"z": (0, 1, 2), "y": (0, 2, 1), "x": (1, 2, 0)}


def to_preview(frame, box=PREVIEW_BOX):
    """A Pillow image of the frame, scaled to fit the box and keep its proportions."""
    from PIL import Image

    if isinstance(frame, ErrorFrame):
        rgb = frame.render(ERROR_FRAME_SIZE)
    else:
        rgb = np.stack([frame, frame, frame], axis=-1)
    image = Image.fromarray(np.ascontiguousarray(rgb, dtype=np.uint8))
    height, width = box
    scale = min(height / image.height, width / image.width)
    size = (max(1, round(image.width * scale)), max(1, round(image.height * scale)))
    return image.resize(size, Image.NEAREST if scale >= 1 else Image.BILINEAR)


def default_output(nrrd_path) -> str:
    """The suggested video file for a volume: next to it, with the same name and .mp4."""
    return str(Path(nrrd_path).with_suffix(".mp4"))


def explore_plane(shape, axis: str = "z", position: float = 0.5, tilt: float = 0.0, top: float = 0.0):
    """An isosceles triangle or trapezoid across the whole volume, for the explore sliders.

    axis      the volume axis the plane cuts across ("x", "y" or "z")
    position  where along that axis the middle of the plane is, 0..1
    tilt      rotation in degrees around the middle line of the plane (0 = a flat slice)
    top       length of the top edge as a part of the base, 0..1: 0 gives a triangle,
              1 a rectangle; anything between is a trapezoid
    The top edge is centred over the base, so both legs are mirror images and equally long,
    and all four points lie on one plane (the plane depends only on v and w, not on u).
    """
    u, v, w = AXES[axis]
    su, sv, sw = shape[u], shape[v], shape[w]
    centre = position * (sw - 1)
    half = math.tan(math.radians(tilt)) * (sv - 1) / 2      # the apex goes up, the base goes down

    def point(pu, pv, pw):
        p = [0.0, 0.0, 0.0]
        p[u], p[v], p[w] = pu, pv, pw
        return tuple(p)

    middle, w_top, w_base = (su - 1) / 2, centre - half, centre + half
    b, c = point(0, sv - 1, w_base), point(su - 1, sv - 1, w_base)
    if top <= 0:
        plane = Triangle(point(middle, 0, w_top), b, c)
    else:
        offset = top * (su - 1) / 2
        plane = Trapezoid(point(middle - offset, 0, w_top), point(middle + offset, 0, w_top), b, c)
    plane.validate()
    return plane


def csv_line(plane) -> str:
    """The plane as one line of a planes CSV file: 9 values for a triangle, 12 for a trapezoid (SRS decision 10)."""
    points = [plane.start1, plane.b, plane.c] if isinstance(plane, Triangle) else \
        [plane.start1, plane.start2, plane.b, plane.c]
    return ",".join(f"{v:.2f}" for p in points for v in p)
