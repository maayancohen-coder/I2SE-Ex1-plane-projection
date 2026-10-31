"""pipeline.run is shared by Ex0.py and the GUI: its messages and its frame callback."""
from pathlib import Path

import numpy as np
import pytest

from nrrd_files import write_nrrd
from projection import pipeline
from projection.errors import VolumeError
from projection.video_writer import ErrorFrame

DATA = Path(__file__).parent / "data"


@pytest.fixture
def volume(tmp_path):
    x, y, z = np.indices((60, 60, 60))
    m = np.where((x - 30) ** 2 + (y - 30) ** 2 + (z - 30) ** 2 < 20 ** 2, 1000, 0).astype(np.uint16)
    return write_nrrd(tmp_path / "ball.nrrd", m)


def test_messages_go_to_log(volume, tmp_path):
    pytest.importorskip("imageio")
    messages = []
    summary = pipeline.run(volume, DATA / "valid_triangles.csv", tmp_path / "out.mp4", log=messages.append)
    assert messages[0].startswith("Loaded ball.nrrd")
    assert messages[-1].startswith("Wrote out.mp4: 5 frames")
    assert summary.frames == summary.projected == 5


def test_on_frame_is_called_for_every_frame_in_order(volume, tmp_path):
    pytest.importorskip("imageio")
    calls = []
    pipeline.run(volume, DATA / "invalid_rows.csv", tmp_path / "out.mp4", log=lambda m: None,
                 on_frame=lambda i, total, frame: calls.append((i, total, type(frame))))
    assert [c[0] for c in calls] == list(range(7))
    assert all(c[1] == 7 for c in calls)
    assert sum(c[2] is ErrorFrame for c in calls) == 6           # one valid row, six error frames


def test_file_errors_are_raised(tmp_path):
    with pytest.raises(VolumeError):
        pipeline.run(tmp_path / "missing.nrrd", DATA / "valid_triangles.csv", tmp_path / "out.mp4", log=lambda m: None)
