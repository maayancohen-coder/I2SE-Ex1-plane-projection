"""
Plane projection of a 3D volume: one video frame for every plane in the CSV file.

Usage:
    python Ex0.py file.nrrd file.csv file.mp4
"""
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from projection import pipeline                                    # noqa: E402
from projection.errors import ProjectionError                      # noqa: E402

USAGE = "Usage: python Ex0.py file.nrrd file.csv file.mp4"


def main(argv: list) -> int:
    if len(argv) != 4:                                               # FR-1
        print(USAGE)
        return 1
    try:
        pipeline.run(*argv[1:])                                      # the messages are printed
    except ProjectionError as e:                                     # FR-3
        print(f"Error: {e}")
        return 1
    except Exception as e:                                           # NFR-2: never a traceback
        print(f"Error: unexpected problem ({type(e).__name__}: {e})")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
