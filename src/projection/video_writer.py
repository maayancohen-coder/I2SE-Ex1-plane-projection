"""Writing a sequence of 2D frames into an mp4 video file: normalisation to 8 bit and padding."""
from pathlib import Path

import numpy as np

from projection.errors import OutputError
from projection.nrrd_reader import Volume

FPS = 10                    # playback rate of the video (SRS 2.2)
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


def frame_size(frames: list) -> tuple:
    """The largest height and width of all frames, rounded up to even numbers (SRS decision 11)."""
    height = max(f.shape[0] for f in frames)
    width = max(f.shape[1] for f in frames)
    return height + height % 2, width + width % 2


def pad(frame: np.ndarray, size: tuple) -> np.ndarray:
    """Place the frame in the centre of a black image of the given size."""
    height, width = size
    out = np.zeros((height, width), dtype=np.uint8)
    top, left = (height - frame.shape[0]) // 2, (width - frame.shape[1]) // 2
    out[top:top + frame.shape[0], left:left + frame.shape[1]] = frame
    return out


class VideoWriter:
    """Writes 8-bit grey frames as an mp4 video: one size for all frames, 10 fps (FR-10)."""

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
                    grey = pad(frame, size)
                    writer.append_data(np.stack([grey, grey, grey], axis=-1))
        except (OSError, RuntimeError, ValueError) as e:
            raise OutputError(f"cannot write the video {path}: {e}") from None
        return size
