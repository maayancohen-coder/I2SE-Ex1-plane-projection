import time
from pathlib import Path

import numpy as np
import pytest

from projection.nrrd_reader import Volume, read_nrrd
from projection.plane import Trapezoid, Triangle
from projection.projector import FastProjector, Layout, ReferenceProjector, round_half_up, sample

DATASET = Path(__file__).parent.parent / "data"
PROJECTORS = [ReferenceProjector(), FastProjector()]


# ---------- helpers [D1, D2] ----------

def test_round_half_up_rounds_to_nearest():
    assert round_half_up(2.4) == 2
    assert round_half_up(2.6) == 3


def test_round_half_up_rounds_halves_up():
    assert round_half_up(2.5) == 3      # Python's round(2.5) would give 2
    assert round_half_up(3.5) == 4


def make_volume():
    """A small 4 x 5 x 6 volume, all zeros except one voxel."""
    m = np.zeros((4, 5, 6), dtype=np.uint8)
    m[1, 2, 3] = 77
    return m


def test_sample_inside_takes_nearest_voxel():
    assert sample(make_volume(), (1.2, 1.6, 3.0)) == 77     # rounds to (1, 2, 3)


def test_sample_outside_returns_zero():
    m = make_volume()
    assert sample(m, (10, 0, 0)) == 0
    assert sample(m, (4, 0, 0)) == 0    # one past the last index (the size is 4)


def test_sample_negative_index_returns_zero():
    m = make_volume()
    m[3, 0, 0] = 99                     # the last x; Python's m[-1] would read it
    assert sample(m, (-1, 0, 0)) == 0


# ---------- the example of docs/ALGORITHM.md: a = (3,0), b = (0,4), c = (6,4) ----------

def example():
    """Dab = 5, Dbc = 6. The volume value is x + 1, so every pixel shows the x it was sampled at."""
    m = (np.arange(7)[:, None, None] + 1) * np.ones((7, 5, 1), dtype=np.uint8)
    return Volume(m.astype(np.uint8)), Triangle((3, 0, 0), (0, 4, 0), (6, 4, 0))


def test_layout_size():
    lay = Layout.of(example()[1])
    assert (lay.height, lay.width) == (6, 7)                # floor(5) + 1 rows, round(6) + 1 columns [D3]


@pytest.mark.parametrize("projector", PROJECTORS)
def test_example_shape(projector):
    e = projector.project(*example())
    expected = ["...#...",
                "..##...",
                "..###..",
                ".####..",
                ".#####.",
                "#######"]
    assert ["".join("#" if v else "." for v in row) for row in e] == expected


@pytest.mark.parametrize("projector", PROJECTORS)
def test_apex_is_one_pixel_in_the_centre(projector):
    e = projector.project(*example())
    assert list(e[0]) == [0, 0, 0, 4, 0, 0, 0]              # the apex a = (3, 0, 0) has value 3 + 1 [D4, D5]


@pytest.mark.parametrize("projector", PROJECTORS)
def test_b_is_left_and_c_is_right(projector):
    e = projector.project(*example())
    assert list(e[-1]) == [1, 2, 3, 4, 5, 6, 7]             # last row: from b (x = 0) to c (x = 6) [D7]


# ---------- known answers ----------

@pytest.mark.parametrize("projector", PROJECTORS)
def test_rectangle_equals_a_slice_of_the_volume(projector):
    m = np.random.default_rng(1).integers(0, 1000, size=(20, 30, 10), dtype=np.uint16)
    rectangle = Trapezoid((0, 0, 5), (19, 0, 5), (0, 29, 5), (19, 29, 5))
    e = projector.project(Volume(m), rectangle)
    assert np.array_equal(e, m[:, :, 5].T)                  # E[y][x] = M[x][y][5]


@pytest.mark.parametrize("projector", PROJECTORS)
def test_plane_outside_the_volume_is_black(projector):
    m = np.full((10, 10, 10), 9, dtype=np.uint8)
    e = projector.project(Volume(m), Triangle((30, 0, 5), (20, 20, 5), (40, 20, 5)))
    assert e.any() == False                                 # FR-8


@pytest.mark.parametrize("projector", PROJECTORS)
def test_plane_partly_outside(projector):
    m = np.full((10, 10, 10), 9, dtype=np.uint8)
    e = projector.project(Volume(m), Triangle((5, -10, 5), (-15, 20, 5), (25, 20, 5)))
    assert set(np.unique(e)) == {0, 9}                      # zeros only where the plane leaves M


def test_nearest_neighbour_creates_no_new_values():
    m = np.random.default_rng(2).choice(np.array([0, 80, 160, 255], dtype=np.uint8), size=(40, 40, 40))
    for plane in random_planes(np.random.default_rng(3), 20, size=40):
        assert set(np.unique(FastProjector().project(Volume(m), plane))) <= {0, 80, 160, 255}


# ---------- reference vs optimised ----------

def random_planes(rng, n, size):
    """Valid random triangles and trapezoids, with decimal coordinates, partly outside a volume of the given size."""
    planes = []
    while len(planes) < n:
        apex = rng.uniform(0, size, 3)
        down = rng.normal(size=3)
        down /= np.linalg.norm(down)
        side = np.cross(down, rng.normal(size=3))
        side /= np.linalg.norm(side)
        height, half_base = rng.uniform(1, size), rng.uniform(0.5, size / 2)
        b = apex + height * down - half_base * side
        c = apex + height * down + half_base * side
        if len(planes) % 2 == 0:
            planes.append(Triangle(apex, b, c))
        else:
            half_top = rng.uniform(0, half_base)
            planes.append(Trapezoid(apex - half_top * side, apex + half_top * side, b, c))
        planes[-1].validate()
    return planes


def test_fast_equals_reference_on_random_planes():
    rng = np.random.default_rng(4)
    volume = Volume(rng.integers(0, 60000, size=(40, 50, 30), dtype=np.uint16))
    for plane in random_planes(rng, 200, size=35):
        assert np.array_equal(FastProjector().project(volume, plane), ReferenceProjector().project(volume, plane))


@pytest.mark.slow
def test_fast_equals_reference_on_mrhead():
    path = DATASET / "MRHead.nrrd"
    if not path.exists():
        pytest.skip("data/MRHead.nrrd not found")
    volume = read_nrrd(path)
    for plane in random_planes(np.random.default_rng(5), 30, size=200):
        assert np.array_equal(FastProjector().project(volume, plane), ReferenceProjector().project(volume, plane))


# ---------- performance (NFR-1) ----------

def crossing_planes(n, size):
    """n triangles that cross the whole volume, tilted a little more each time."""
    planes = []
    for t in np.linspace(0, 1, n):
        z_top, z_bottom = t * (size - 1), (1 - t) * (size - 1)
        planes.append(Triangle((size / 2, 0, z_top), (0, size - 1, z_bottom), (size - 1, size - 1, z_bottom)))
    return planes


@pytest.mark.slow
def test_performance_on_croissant():
    path = DATASET / "croissant.nrrd"
    if not path.exists():
        pytest.skip("data/croissant.nrrd not found")
    volume = read_nrrd(path)
    planes = crossing_planes(100, volume.shape[0])
    projector = FastProjector()
    projector.project(volume, planes[0])                    # warm-up
    start = time.perf_counter()
    for plane in planes:
        projector.project(volume, plane)
    fps = len(planes) / (time.perf_counter() - start)
    print(f"\nFastProjector on croissant.nrrd (500^3): {fps:.1f} fps")
    assert fps >= 30
