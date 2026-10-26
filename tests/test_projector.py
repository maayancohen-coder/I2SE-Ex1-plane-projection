import numpy as np

from projection.projector import round_half_up, sample


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