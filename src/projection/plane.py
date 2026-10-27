"""The projection plane: triangle or trapezoid, built from 3 or 4 points, with input validation."""
import csv
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

import numpy as np

from projection.errors import PlaneError, PlaneFileError

TOLERANCE = 1e-3   # allowed difference for user input; the EPS = 0.001 of the assignment Q&A
EPSILON = 1e-9     # tolerance for comparing computed floating-point values to zero


def dist(p, q) -> float:
    """Euclidean distance between two 3D points."""
    dx, dy, dz = q[0] - p[0], q[1] - p[1], q[2] - p[2]
    return math.sqrt(dx * dx + dy * dy + dz * dz)


class Plane(ABC):
    """A plane described by two legs: start1 -> b and start2 -> c.

    The projection algorithm only uses these four points, so it works the same way
    for every kind of plane (polymorphism, see docs/DESIGN.md).
    """

    def __init__(self, start1, start2, b, c):
        self._start1 = np.array(start1, dtype=float)
        self._start2 = np.array(start2, dtype=float)
        self._b = np.array(b, dtype=float)
        self._c = np.array(c, dtype=float)

    @property
    def start1(self) -> np.ndarray:
        return self._start1

    @property
    def start2(self) -> np.ndarray:
        return self._start2

    @property
    def b(self) -> np.ndarray:
        return self._b

    @property
    def c(self) -> np.ndarray:
        return self._c

    @abstractmethod
    def validate(self) -> None:
        """Raise PlaneError if the plane breaks a rule of SRS decision 9."""


class Triangle(Plane):
    """Isosceles triangle a, b, c with |ab| = |ac|. Both legs start at the apex a."""

    def __init__(self, a, b, c):
        super().__init__(a, a, b, c)

    @property
    def a(self) -> np.ndarray:
        return self.start1

    def validate(self) -> None:
        a, b, c = self.a, self.b, self.c
        leg_ab, leg_ac = dist(a, b), dist(a, c)
        if abs(leg_ab - leg_ac) >= TOLERANCE:
            raise PlaneError(f"not isosceles: |ab| = {leg_ab:.4f}, |ac| = {leg_ac:.4f}")
        if np.linalg.norm(np.cross(b - a, c - a)) < TOLERANCE:
            raise PlaneError("degenerate triangle: the points are collinear or identical")


class Trapezoid(Plane):
    """Isosceles trapezoid a', a'', b, c with legs a'->b and a''->c (assignment Q&A)."""

    def validate(self) -> None:
        a1, a2, b, c = self.start1, self.start2, self.b, self.c
        leg1, leg2 = dist(a1, b), dist(a2, c)
        if abs(leg1 - leg2) >= TOLERANCE:
            raise PlaneError(f"legs not equal: |a'b| = {leg1:.4f}, |a''c| = {leg2:.4f}")
        top, base = dist(a1, a2), dist(b, c)
        if top > base + EPSILON:
            raise PlaneError(f"top edge longer than the base: |a'a''| = {top:.4f}, |bc| = {base:.4f}")
        normal = np.cross(b - a1, c - a1)
        normal_length = np.linalg.norm(normal)
        if normal_length < TOLERANCE:
            raise PlaneError("degenerate trapezoid: a', b, c are collinear or identical")
        distance = abs(np.dot(a2 - a1, normal)) / normal_length
        if distance >= TOLERANCE:
            raise PlaneError(f"the four points are not on one plane (a'' is {distance:.4f} away)")
        
        
@dataclass(frozen=True)
class PlaneRow:
    """One plane line of the CSV file: either a valid plane or the reason it is invalid."""
    line: int                    # line number in the CSV file, starting at 1 (SRS decision 9)
    plane: Optional[Plane]
    error: Optional[str]

    @property
    def is_valid(self) -> bool:
        return self.plane is not None


def plane_from_values(values: Sequence[float]) -> Plane:
    """Build a Triangle (9 values) or a Trapezoid (12 values) and validate it."""
    points = [values[i:i + 3] for i in range(0, len(values), 3)]
    if len(points) == 3:
        plane = Triangle(*points)
    elif len(points) == 4:
        plane = Trapezoid(*points)
    else:
        raise PlaneError(f"expected 9 or 12 values, got {len(values)}")
    plane.validate()
    return plane


def parse_row(fields: Sequence[str]) -> Plane:
    """Turn the fields of one CSV line into a valid plane, or raise PlaneError."""
    if len(fields) not in (9, 12):
        raise PlaneError(f"expected 9 or 12 values, got {len(fields)}")
    values = []
    for field in fields:
        try:
            value = float(field)
        except ValueError:
            raise PlaneError(f"not a number: {field.strip()!r}") from None
        if not math.isfinite(value):
            raise PlaneError(f"not a finite number: {field.strip()!r}")
        values.append(value)
    return plane_from_values(values)


def parse_planes(path) -> list:
    """Read the planes of a CSV file (SRS decision 10).

    Returns a PlaneRow for every line that is not empty and not a comment.
    Raises PlaneFileError if the file cannot be read or contains no planes.
    """
    path = Path(path)
    try:
        with path.open(newline="", encoding="utf-8-sig") as f:
            lines = list(csv.reader(f))
    except (OSError, UnicodeDecodeError, csv.Error) as e:
        raise PlaneFileError(f"cannot read the CSV file {path}: {e}") from None

    rows = []
    for number, fields in enumerate(lines, start=1):
        if not fields or all(not field.strip() for field in fields):
            continue                                    # empty line
        if fields[0].lstrip().startswith("#"):
            continue                                    # comment
        try:
            rows.append(PlaneRow(number, parse_row(fields), None))
        except PlaneError as e:
            rows.append(PlaneRow(number, None, str(e)))

    if not rows:
        raise PlaneFileError(f"the CSV file {path} contains no planes")
    return rows