"""The parts of the GUI that do not need a window (projection.preview)."""
import numpy as np
import pytest

from projection.plane import Trapezoid, Triangle, parse_row
from projection.preview import csv_line, default_output, explore_plane, to_preview
from projection.video_writer import ErrorFrame


def test_preview_keeps_the_proportions():
    pytest.importorskip("PIL")
    image = to_preview(np.zeros((100, 200), dtype=np.uint8), box=(360, 360))
    assert image.size == (360, 180)                             # Pillow sizes are (width, height)


def test_preview_of_a_small_frame_is_enlarged():
    pytest.importorskip("PIL")
    image = to_preview(np.full((10, 10), 7, dtype=np.uint8), box=(100, 100))
    assert image.size == (100, 100)
    assert image.getpixel((50, 50)) == (7, 7, 7)                # nearest: no new values


def test_preview_of_an_error_frame_is_red_and_black():
    pytest.importorskip("PIL")
    image = np.asarray(to_preview(ErrorFrame("f.csv line 2", "bad"), box=(240, 320)))
    assert image.shape == (240, 320, 3)
    assert ((image[:, :, 0] > 150) & (image[:, :, 1] < 100)).any()


def test_default_output_is_next_to_the_volume():
    assert default_output("data/MRHead.nrrd").replace("\\", "/") == "data/MRHead.mp4"


# ---------- explore sliders ----------

def test_flat_plane_is_a_slice_in_the_middle():
    plane = explore_plane((256, 256, 130), axis="z", position=0.5, tilt=0)
    assert {p[2] for p in (plane.start1, plane.b, plane.c)} == {64.5}     # z = 0.5 * 129 for every point


@pytest.mark.parametrize("axis", ["x", "y", "z"])
@pytest.mark.parametrize("tilt", [-60, -15, 0, 30, 60])
def test_explore_planes_are_valid(axis, tilt):
    explore_plane((100, 80, 60), axis=axis, position=0.3, tilt=tilt)      # validate() raises if not


@pytest.mark.parametrize("axis, moving", [("x", 0), ("y", 1), ("z", 2)])
def test_position_moves_along_the_chosen_axis(axis, moving):
    low = explore_plane((100, 80, 60), axis=axis, position=0.0)
    high = explore_plane((100, 80, 60), axis=axis, position=1.0)
    assert low.start1[moving] == 0
    assert high.start1[moving] == (100, 80, 60)[moving] - 1


def test_csv_line_can_be_read_back():
    plane = explore_plane((256, 256, 130), axis="y", position=0.25, tilt=20)
    assert np.allclose(parse_row(csv_line(plane).split(",")).b, plane.b, atol=0.01)


@pytest.mark.parametrize("axis", ["x", "y", "z"])
@pytest.mark.parametrize("tilt", [-45, 0, 30])
@pytest.mark.parametrize("top", [0.1, 0.5, 1.0])
def test_explore_trapezoids_are_valid(axis, tilt, top):
    plane = explore_plane((100, 80, 60), axis=axis, position=0.6, tilt=tilt, top=top)
    assert isinstance(plane, Trapezoid)                     # validate() already checked legs, top and coplanarity


def test_top_zero_is_a_triangle():
    assert isinstance(explore_plane((50, 50, 50), top=0), Triangle)


def test_full_top_is_the_whole_slice():
    """A flat rectangle (top = 1, tilt = 0) is exactly the slice z = 30 of the volume."""
    from projection.nrrd_reader import Volume
    from projection.projector import FastProjector
    m = np.random.default_rng(3).integers(0, 255, (40, 30, 61)).astype(np.uint8)
    plane = explore_plane(m.shape, axis="z", position=0.5, tilt=0, top=1.0)
    image = FastProjector().project(Volume(m), plane)
    assert np.array_equal(image, m[:, :, 30].T)             # E[y][x] = M[x][y][z]


def test_trapezoid_csv_line_has_12_values():
    plane = explore_plane((256, 256, 130), axis="z", position=0.4, tilt=10, top=0.5)
    line = csv_line(plane)
    assert len(line.split(",")) == 12
    assert np.allclose(parse_row(line.split(",")).start2, plane.start2, atol=0.01)
