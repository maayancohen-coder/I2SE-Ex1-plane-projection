from pathlib import Path

import pytest

from projection.errors import PlaneError, PlaneFileError
from projection.plane import Trapezoid, Triangle, parse_planes

DATA = Path(__file__).parent / "data"


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
        
        # ---------- CSV files ----------

def test_all_valid_triangles_in_file():
    rows = parse_planes(DATA / "valid_triangles.csv")
    assert len(rows) == 5
    assert all(row.is_valid for row in rows)
    assert all(isinstance(row.plane, Triangle) for row in rows)


def test_all_valid_trapezoids_in_file():
    rows = parse_planes(DATA / "valid_trapezoids.csv")
    assert len(rows) == 4
    assert all(row.is_valid for row in rows)
    assert all(isinstance(row.plane, Trapezoid) for row in rows)


def test_outside_planes_are_valid():
    rows = parse_planes(DATA / "outside.csv")
    assert all(row.is_valid for row in rows)


def test_every_invalid_plane_is_rejected():
    rows = parse_planes(DATA / "invalid_planes.csv")
    assert len(rows) == 8
    assert not any(row.is_valid for row in rows)


def test_invalid_rows_keep_their_line_numbers():
    rows = parse_planes(DATA / "invalid_rows.csv")
    # every non-comment line is a row; the line numbers are the lines in the file
    assert [row.line for row in rows] == [4, 6, 8, 10, 12, 14, 16]
    assert [row.is_valid for row in rows] == [False, True, False, False, False, False, False]


def test_invalid_row_messages():
    rows = parse_planes(DATA / "invalid_rows.csv")
    errors = [row.error for row in rows if not row.is_valid]
    assert "expected 9 or 12 values, got 8" in errors[0]
    assert "not a number" in errors[3]


def test_no_planes_is_a_file_error():
    with pytest.raises(PlaneFileError, match="no planes"):
        parse_planes(DATA / "no_planes.csv")


def test_missing_csv_is_a_file_error(tmp_path):
    with pytest.raises(PlaneFileError):
        parse_planes(tmp_path / "missing.csv")


def test_spaces_and_windows_line_endings(tmp_path):
    f = tmp_path / "planes.csv"
    f.write_bytes(b"# comment\r\n100, 10, 100, 20, 190, 100, 180, 190, 100\r\n")
    rows = parse_planes(f)
    assert len(rows) == 1 and rows[0].is_valid and rows[0].line == 2