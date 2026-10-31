"""The parts of the GUI that do not need a window (projection.preview)."""
import numpy as np
import pytest

from projection.preview import default_output, to_preview
from projection.video_writer import ErrorFrame

pytest.importorskip("PIL")


def test_preview_keeps_the_proportions():
    image = to_preview(np.zeros((100, 200), dtype=np.uint8), box=(360, 360))
    assert image.size == (360, 180)                             # Pillow sizes are (width, height)


def test_preview_of_a_small_frame_is_enlarged():
    image = to_preview(np.full((10, 10), 7, dtype=np.uint8), box=(100, 100))
    assert image.size == (100, 100)
    assert image.getpixel((50, 50)) == (7, 7, 7)                # nearest: no new values


def test_preview_of_an_error_frame_is_red_and_black():
    image = np.asarray(to_preview(ErrorFrame("f.csv line 2", "bad"), box=(240, 320)))
    assert image.shape == (240, 320, 3)
    assert ((image[:, :, 0] > 150) & (image[:, :, 1] < 100)).any()


def test_default_output_is_next_to_the_volume():
    assert default_output("data/MRHead.nrrd").replace("\\", "/") == "data/MRHead.mp4"
