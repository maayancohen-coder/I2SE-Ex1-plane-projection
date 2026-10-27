"""The projection plane: triangle or trapezoid, built from 3 or 4 points, with input validation."""
import math
from abc import ABC, abstractmethod

import numpy as np

from projection.errors import PlaneError

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