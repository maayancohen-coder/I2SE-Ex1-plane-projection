import pytest

from projection.errors import PlaneError
from projection.plane import Trapezoid, Triangle


# ---------- valid planes ----------

def test_triangle_legs_start_at_apex():
    t = Triangle((100, 10, 100), (20, 190, 100), (180, 190, 100))
    t.validate()
    assert list(t.start1) == list(t.start2) == [100, 10, 100]


def test_trapezoid_legs_start_at_top_corners():
    t = Trapezoid((70, 40, 100), (130, 40, 100), (20, 160, 100), (180, 160, 100))
    t.validate()
    assert list(t.start1) == [70, 40, 100]
    assert list(t.start2) == [130, 40, 100]


def test_rectangle_is_valid():
    # top edge = base is allowed (assignment Q&A: dist(a1, a2) <= dist(b, c))
    Trapezoid((40, 30, 100), (160, 30, 100), (40, 170, 100), (160, 170, 100)).validate()


# ---------- TOLERANCE boundary ----------

def test_leg_difference_below_tolerance_is_valid():
    Triangle((100, 10, 100), (20, 190, 100), (180.0012, 190, 100)).validate()     # difference 0.0005


def test_leg_difference_above_tolerance_is_invalid():
    with pytest.raises(PlaneError):
        Triangle((100, 10, 100), (20, 190, 100), (180.005, 190, 100)).validate()  # difference 0.002


# ---------- invalid planes: each one breaks exactly one rule ----------

@pytest.mark.parametrize("points, reason", [
    ([(100, 10, 100), (20, 190, 100), (150, 190, 100)], "not isosceles"),
    ([(100, 100, 100), (50, 100, 100), (150, 100, 100)], "degenerate"),       # collinear
    ([(100, 10, 100), (100, 190, 100), (100, 190, 100)], "degenerate"),       # b = c
    ([(100, 100, 100)] * 3, "degenerate"),                                    # identical points
])
def test_invalid_triangle(points, reason):
    with pytest.raises(PlaneError, match=reason):
        Triangle(*points).validate()


@pytest.mark.parametrize("points, reason", [
    ([(70, 40, 100), (140, 40, 100), (20, 160, 100), (180, 160, 100)], "legs not equal"),
    ([(20, 40, 100), (180, 40, 100), (70, 160, 100), (130, 160, 100)], "top edge longer"),
    ([(70, 40, 100), (131.0102051, 40, 110), (20, 160, 100), (180, 160, 100)], "not on one plane"),
])
def test_invalid_trapezoid(points, reason):
    with pytest.raises(PlaneError, match=reason):
        Trapezoid(*points).validate()