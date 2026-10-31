"""Writing a sequence of 2D frames into an mp4 video file: normalisation to 8 bit, padding and error frames."""
import textwrap
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from projection.errors import OutputError
from projection.nrrd_reader import Volume

FPS = 10                    # playback rate of the video (SRS 2.2)
ERROR_FRAME_SIZE = (240, 320)   # frame size when every row of the CSV file is invalid
LOW_PERCENTILE = 0.5        # SRS decision 8
HIGH_PERCENTILE = 99.5


class Normalizer:
    """Maps the values of one volume to 0..255 with one mapping for all frames (SRS decision 8)."""

    def __init__(self, volume: Volume):
        data = volume.data
        self._identity = data.dtype == np.uint8         # uint8 volumes are used as is
        self._lo = self._hi = 0.0
        if self._identity:
            return
        lo, hi = np.percentile(data, [LOW_PERCENTILE, HIGH_PERCENTILE])
        if hi == lo:                                    # fallback: e.g. a volume more than 99.5% empty
            lo, hi = data.min(), data.max()
        self._lo, self._hi = float(lo), float(hi)

    @property
    def range(self) -> tuple:
        """(lo, hi) of the mapping; (0, 0) for a uint8 volume."""
        return self._lo, self._hi

    def to_uint8(self, image: np.ndarray) -> np.ndarray:
        if self._identity:
            return image.astype(np.uint8, copy=False)
        if self._hi == self._lo:                        # a constant volume: nothing to show
            return np.zeros(image.shape, dtype=np.uint8)
        scaled = (image.astype(np.float64) - self._lo) / (self._hi - self._lo) * 255
        return np.clip(np.floor(scaled + 0.5), 0, 255).astype(np.uint8)


@dataclass(frozen=True)
class ErrorFrame:
    """The frame of an invalid CSV row: black, with a red X, the line and the reason (SRS decision 9)."""
    title: str          # e.g. "planes.csv line 12"
    reason: str         # e.g. "not a number: 'abc'"

    def render(self, size: tuple) -> np.ndarray:
        """Draw the frame at the given (height, width) as an RGB image."""
        from PIL import Image, ImageDraw, ImageFont     # Pillow is installed together with imageio

        height, width = size
        image = Image.new("RGB", (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(image)
        red = (230, 60, 50)
        line_width = max(3, min(height, width) // 60)      # thick enough to survive video compression
        draw.line([(0, 0), (width - 1, height - 1)], fill=red, width=line_width)
        draw.line([(0, height - 1), (width - 1, 0)], fill=red, width=line_width)

        font_size = max(8, min(width // 20, height // 10))
        try:
            font = ImageFont.load_default(size=font_size)
        except TypeError:                               # older Pillow: one fixed size
            font = ImageFont.load_default()
        chars_per_line = max(10, int(width / (font_size * 0.55)))
        lines = ["INVALID PLANE", self.title, *textwrap.wrap(self.reason, chars_per_line)]
        step = font_size + font_size // 3
        y = (height - step * len(lines)) // 2
        for text in lines:
            text_width = draw.textlength(text, font=font)
            x = (width - text_width) / 2
            draw.rectangle([x - 3, y - 1, x + text_width + 3, y + step - 1], fill=(0, 0, 0))
            draw.text((x, y), text, fill=(255, 255, 255), font=font)
            y += step
        return np.asarray(image)


def frame_size(frames: list) -> tuple:
    """The largest height and width of all image frames, rounded up to even numbers (SRS decision 11)."""
    images = [f for f in frames if not isinstance(f, ErrorFrame)]
    if not images:
        return ERROR_FRAME_SIZE
    height = max(f.shape[0] for f in images)
    width = max(f.shape[1] for f in images)
    return height + height % 2, width + width % 2


def pad(frame: np.ndarray, size: tuple) -> np.ndarray:
    """Place the frame in the centre of a black image of the given size."""
    height, width = size
    out = np.zeros((height, width), dtype=np.uint8)
    top, left = (height - frame.shape[0]) // 2, (width - frame.shape[1]) // 2
    out[top:top + frame.shape[0], left:left + frame.shape[1]] = frame
    return out


class VideoWriter:
    """Writes 8-bit grey frames and error frames as an mp4 video: one size for all frames, 10 fps (FR-10)."""

    def __init__(self, fps: int = FPS):
        self.fps = fps

    def write(self, path, frames: list) -> tuple:
        """Write the frames in order and return the frame size (height, width)."""
        import imageio.v2 as imageio        # imported here so the rest of the program does not need it

        if not frames:
            raise OutputError("there are no frames to write")
        path = Path(path)
        size = frame_size(frames)
        try:
            with imageio.get_writer(path, fps=self.fps, codec="libx264", quality=8,
                                    macro_block_size=1, pixelformat="yuv420p") as writer:
                for frame in frames:
                    if isinstance(frame, ErrorFrame):
                        writer.append_data(frame.render(size))
                    else:
                        grey = pad(frame, size)
                        writer.append_data(np.stack([grey, grey, grey], axis=-1))
        except (OSError, RuntimeError, ValueError) as e:
            raise OutputError(f"cannot write the video {path}: {e}") from None
        return size
