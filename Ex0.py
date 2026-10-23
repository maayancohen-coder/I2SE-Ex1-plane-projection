"""
Demo entry point.

Usage:
    python Ex0.py file.nrrd file.csv file.mp4
"""
import sys


def main(argv):
    if len(argv) != 4:
        print(__doc__)
        return 1
    nrrd_path, csv_path, mp4_path = argv[1:]
    # TODO: read volume, read planes, project each plane, write video
    print(f"volume: {nrrd_path}\nplanes: {csv_path}\noutput: {mp4_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
