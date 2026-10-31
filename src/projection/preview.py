"""Helpers of the GUI that do not need a window, so they can be tested anywhere."""
from pathlib import Path

import numpy as np

from projection.video_writer import ERROR_FRAME_SIZE, ErrorFrame

PREVIEW_BOX = (360, 360)        # (height, width) of the preview area in the window


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
