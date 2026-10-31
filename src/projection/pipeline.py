"""The whole program as one function: volume + planes -> video.

Shared by the command line (Ex0.py) and the window (gui.py), so both run exactly the same code.
"""
import time
from dataclasses import dataclass
from pathlib import Path

from projection.nrrd_reader import read_nrrd
from projection.plane import parse_planes
from projection.projector import FastProjector
from projection.video_writer import ErrorFrame, Normalizer, VideoWriter


@dataclass(frozen=True)
class Summary:
    """What one run produced."""
    frames: int             # frames in the video, error frames included
    projected: int          # valid planes
    average: float          # seconds per projected plane (0 if none)
    size: tuple             # (height, width) of the video


def run(nrrd_path, csv_path, mp4_path, log=print, on_frame=None) -> Summary:
    """Project every plane of the CSV file and write the video.

    log(message)                    receives every line that the program reports
    on_frame(index, total, frame)   is called after each frame; frame is a uint8 image or an ErrorFrame
    Raises a ProjectionError if a file cannot be read or written (FR-3).
    """
    csv_name = Path(csv_path).name

    start = time.perf_counter()
    volume = read_nrrd(nrrd_path)
    read_time = time.perf_counter() - start
    sx, sy, sz = volume.shape
    log(f"Loaded {Path(nrrd_path).name}: {sx} x {sy} x {sz}, {volume.dtype} ({read_time:.2f} s)")

    rows = parse_planes(csv_path)
    normalizer = Normalizer(volume)
    projector = FastProjector()

    frames, projection_time, projected = [], 0.0, 0
    for index, row in enumerate(rows):
        if row.is_valid:
            start = time.perf_counter()
            image = projector.project(volume, row.plane)
            projection_time += time.perf_counter() - start          # only the projection is timed
            projected += 1
            frame = normalizer.to_uint8(image)
        else:                                                       # SRS decision 9
            log(f"Warning: {csv_name} line {row.line}: {row.error} -> error frame")
            frame = ErrorFrame(f"{csv_name} line {row.line}", row.error)
        frames.append(frame)
        if on_frame is not None:
            on_frame(index, len(rows), frame)

    start = time.perf_counter()
    height, width = VideoWriter().write(mp4_path, frames)
    write_time = time.perf_counter() - start

    # timing summary (FR-11)
    average = projection_time / projected if projected else 0.0
    if projected:
        log(f"Projected {projected} plane(s): average {average * 1000:.2f} ms per plane ({1 / average:.0f} fps)")
    else:
        log("Projected 0 planes: every row was invalid")
    log(f"Wrote {Path(mp4_path).name}: {len(frames)} frames of {width} x {height} ({write_time:.2f} s)")
    return Summary(len(frames), projected, average, (height, width))
