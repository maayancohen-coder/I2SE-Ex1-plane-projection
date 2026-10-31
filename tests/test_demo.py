"""Demo tests: Ex0.py is run as a separate process, exactly as the lecturer runs it (TESTING.md, level 5)."""
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from nrrd_files import write_nrrd

ROOT = Path(__file__).parent.parent
DATA = Path(__file__).parent / "data"


def run_demo(*args):
    result = subprocess.run([sys.executable, str(ROOT / "Ex0.py"), *map(str, args)],
                            capture_output=True, text=True, timeout=300)
    return result.returncode, result.stdout + result.stderr


@pytest.fixture
def volume(tmp_path):
    """A small 16-bit volume (200 x 200 x 200 like the phantom) with a bright ball in the centre."""
    x, y, z = np.indices((200, 200, 200))
    m = np.where((x - 100) ** 2 + (y - 100) ** 2 + (z - 100) ** 2 < 60 ** 2, 1000, 0).astype(np.uint16)
    return write_nrrd(tmp_path / "ball.nrrd", m)


def count_frames(path):
    imageio = pytest.importorskip("imageio.v2")
    with imageio.get_reader(path) as reader:
        frames = [frame for frame in reader]
    return len(frames), frames[0].shape[:2]


def test_valid_input_creates_the_video(volume, tmp_path):
    out = tmp_path / "out.mp4"
    code, output = run_demo(volume, DATA / "valid_triangles.csv", out)
    assert code == 0, output
    assert out.exists()
    frames, (height, width) = count_frames(out)
    assert frames == 5                                       # one frame per plane (FR-10)
    assert height % 2 == 0 and width % 2 == 0


def test_timing_summary_is_printed(volume, tmp_path):
    code, output = run_demo(volume, DATA / "valid_trapezoids.csv", tmp_path / "out.mp4")
    assert code == 0, output
    assert "Loaded ball.nrrd" in output                      # FR-11
    assert "ms per plane" in output and "fps" in output
    assert "Wrote out.mp4: 4 frames" in output


@pytest.mark.parametrize("args", [[], ["a.nrrd"], ["a.nrrd", "b.csv"], ["a", "b", "c", "d"]])
def test_wrong_number_of_arguments(args):
    code, output = run_demo(*args)
    assert code != 0
    assert "Usage: python Ex0.py file.nrrd file.csv file.mp4" in output      # FR-1
    assert "Traceback" not in output


def test_missing_nrrd_file(tmp_path):
    code, output = run_demo(tmp_path / "missing.nrrd", DATA / "valid_triangles.csv", tmp_path / "out.mp4")
    assert code != 0 and output.startswith("Error:") and "Traceback" not in output   # FR-3, NFR-2
    assert not (tmp_path / "out.mp4").exists()


def test_missing_csv_file(volume, tmp_path):
    code, output = run_demo(volume, tmp_path / "missing.csv", tmp_path / "out.mp4")
    assert code != 0 and "Error:" in output and "Traceback" not in output
    assert not (tmp_path / "out.mp4").exists()


def test_csv_without_planes(volume, tmp_path):
    code, output = run_demo(volume, DATA / "no_planes.csv", tmp_path / "out.mp4")
    assert code != 0 and "no planes" in output and "Traceback" not in output
    assert not (tmp_path / "out.mp4").exists()


def test_invalid_rows_give_warnings_and_black_frames(volume, tmp_path):
    out = tmp_path / "out.mp4"
    code, output = run_demo(volume, DATA / "invalid_rows.csv", out)
    assert code == 0, output
    warned = [line for line in output.splitlines() if line.startswith("Warning:")]
    assert [w.split("line ")[1].split(":")[0] for w in warned] == ["4", "8", "10", "12", "14", "16"]   # FR-5
    assert count_frames(out)[0] == 7                         # the valid row 6 keeps its place


def test_invalid_planes_give_warnings(volume, tmp_path):
    code, output = run_demo(volume, DATA / "invalid_planes.csv", tmp_path / "out.mp4")
    assert code == 0, output
    assert output.count("Warning:") == 8
