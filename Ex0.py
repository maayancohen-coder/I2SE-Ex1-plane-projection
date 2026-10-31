"""
Plane projection of a 3D volume: one video frame for every plane in the CSV file.

Usage:
    python Ex0.py file.nrrd file.csv file.mp4
"""
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from projection.errors import ProjectionError                      # noqa: E402
from projection.nrrd_reader import read_nrrd                       # noqa: E402
from projection.plane import parse_planes                          # noqa: E402
from projection.projector import FastProjector                     # noqa: E402
from projection.video_writer import Normalizer, VideoWriter        # noqa: E402

USAGE = "Usage: python Ex0.py file.nrrd file.csv file.mp4"
BLACK_FRAME = np.zeros((2, 2), dtype=np.uint8)   # padded to the full frame size by the writer


def run(nrrd_path: str, csv_path: str, mp4_path: str) -> None:
    start = time.perf_counter()
    volume = read_nrrd(nrrd_path)
    read_time = time.perf_counter() - start
    sx, sy, sz = volume.shape
    print(f"Loaded {Path(nrrd_path).name}: {sx} x {sy} x {sz}, {volume.dtype} ({read_time:.2f} s)")

    rows = parse_planes(csv_path)
    normalizer = Normalizer(volume)
    projector = FastProjector()

    frames, projection_time, projected = [], 0.0, 0
    for row in rows:
        if not row.is_valid:                                         # SRS decision 9
            print(f"Warning: {Path(csv_path).name} line {row.line}: {row.error} -> black frame")
            frames.append(BLACK_FRAME)
            continue
        start = time.perf_counter()
        image = projector.project(volume, row.plane)
        projection_time += time.perf_counter() - start
        projected += 1
        frames.append(normalizer.to_uint8(image))

    start = time.perf_counter()
    height, width = VideoWriter().write(mp4_path, frames)
    write_time = time.perf_counter() - start

    # timing summary (FR-11)
    if projected:
        average = projection_time / projected
        print(f"Projected {projected} planes: average {average * 1000:.2f} ms per plane ({1 / average:.0f} fps)")
    else:
        print("Projected 0 planes: every row was invalid")
    print(f"Wrote {Path(mp4_path).name}: {len(frames)} frames of {width} x {height} ({write_time:.2f} s)")


def main(argv: list) -> int:
    if len(argv) != 4:                                               # FR-1
        print(USAGE)
        return 1
    try:
        run(*argv[1:])
    except ProjectionError as e:                                     # FR-3
        print(f"Error: {e}")
        return 1
    except Exception as e:                                           # NFR-2: never a traceback
        print(f"Error: unexpected problem ({type(e).__name__}: {e})")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
