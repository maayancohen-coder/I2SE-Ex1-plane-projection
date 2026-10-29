"""The projection algorithm: sampling a plane of the volume into a 2D image E.

See docs/ALGORITHM.md. Decisions of the SRS are referred to as [D1] .. [D11].
"""
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

import numpy as np

from projection.nrrd_reader import Volume
from projection.plane import EPSILON, Plane, dist


def round_half_up(v: float) -> int:
    """Round to the nearest integer; exact halves round up (2.5 -> 3). SRS decision 2."""
    return math.floor(v + 0.5)


def sample(m: np.ndarray, p) -> int:
    """Value of the volume m at point p (nearest voxel), or 0 if p is outside m. SRS decision 1."""
    i, j, k = round_half_up(p[0]), round_half_up(p[1]), round_half_up(p[2])
    sx, sy, sz = m.shape
    if 0 <= i < sx and 0 <= j < sy and 0 <= k < sz:
        return int(m[i, j, k])
    return 0


@dataclass(frozen=True)
class Layout:
    """Sizes and unit vectors of a plane (steps 1-3 of the algorithm), shared by both projectors."""
    start1: np.ndarray
    start2: np.ndarray
    v_ab: np.ndarray        # unit step down the leg start1 -> b
    v_ac: np.ndarray        # unit step down the leg start2 -> c
    dbc: float
    height: int             # floor(Dab) + 1 rows [D3, D4]
    width: int              # round(Dbc) + 1 columns [D2, D3]

    @staticmethod
    def of(plane: Plane) -> "Layout":
        dab = dist(plane.start1, plane.b)
        dbc = dist(plane.b, plane.c)
        return Layout(
            start1=plane.start1,
            start2=plane.start2,
            v_ab=(plane.b - plane.start1) / dab,
            v_ac=(plane.c - plane.start2) / dab,
            dbc=dbc,
            height=math.floor(dab) + 1,
            width=round_half_up(dbc) + 1,
        )


class Projector(ABC):
    """Interface of the projection: one plane of a volume -> a 2D image E[y][x] [D7]."""

    @abstractmethod
    def project(self, volume: Volume, plane: Plane) -> np.ndarray:
        """Return E with the same value type as the volume; pixels outside the plane or M are 0."""


class ReferenceProjector(Projector):
    """A direct translation of docs/ALGORITHM.md with plain loops.

    Simple and slow: used as the reference that FastProjector is tested against.
    """

    def project(self, volume: Volume, plane: Plane) -> np.ndarray:
        m = volume.data
        lay = Layout.of(plane)
        e = np.zeros((lay.height, lay.width), dtype=m.dtype)

        for y in range(lay.height):
            a1 = lay.start1 + y * lay.v_ab              # sample first, then step [D4]
            a2 = lay.start2 + y * lay.v_ac
            d12 = dist(a1, a2)

            if d12 < EPSILON:                           # single-point row, e.g. the apex [D5]
                self._put(e, y, round_half_up(lay.dbc / 2), sample(m, a1))
                continue

            dp = (a2 - a1) / d12
            for x1 in range(math.floor(d12) + 1):
                p = a1 + x1 * dp
                x = round_half_up(lay.dbc / 2 - d12 / 2 + x1)     # centre the row [D2]
                self._put(e, y, x, sample(m, p))
        return e

    @staticmethod
    def _put(e: np.ndarray, y: int, x: int, value: int) -> None:
        if 0 <= x < e.shape[1]:
            e[y, x] = value


class FastProjector(Projector):
    """The same algorithm, computed for all pixels at once with numpy (NFR-1).

    Every arithmetic step is written in the same order as in ReferenceProjector,
    so both return exactly the same image.
    """

    def project(self, volume: Volume, plane: Plane) -> np.ndarray:
        m = volume.data
        lay = Layout.of(plane)
        e = np.zeros((lay.height, lay.width), dtype=m.dtype)

        y = np.arange(lay.height, dtype=float)[:, None]
        a1 = lay.start1 + y * lay.v_ab                          # one row per line of E
        a2 = lay.start2 + y * lay.v_ac
        d = a2 - a1
        d12 = np.sqrt(d[:, 0] * d[:, 0] + d[:, 1] * d[:, 1] + d[:, 2] * d[:, 2])

        single = d12 < EPSILON                                  # single-point rows [D5]
        d12 = np.where(single, 0.0, d12)
        dp = np.where(single[:, None], 0.0, d / np.where(single, 1.0, d12)[:, None])

        count = np.floor(d12).astype(np.int64) + 1              # samples per row
        x1 = np.arange(count.max(), dtype=float)[None, :]
        used = x1 < count[:, None]                              # rows have different lengths

        # p = a1 + x1 * dp for every row and every step, one coordinate at a time
        i = np.floor(a1[:, 0:1] + x1 * dp[:, 0:1] + 0.5).astype(np.int64)
        j = np.floor(a1[:, 1:2] + x1 * dp[:, 1:2] + 0.5).astype(np.int64)
        k = np.floor(a1[:, 2:3] + x1 * dp[:, 2:3] + 0.5).astype(np.int64)
        x = np.floor(lay.dbc / 2 - d12[:, None] / 2 + x1 + 0.5).astype(np.int64)

        sx, sy, sz = m.shape
        inside = used & (i >= 0) & (i < sx) & (j >= 0) & (j < sy) & (k >= 0) & (k < sz)
        write = used & (x >= 0) & (x < lay.width)

        values = np.zeros(i.shape, dtype=m.dtype)
        values[inside] = m[i[inside], j[inside], k[inside]]    # nearest voxel, 0 outside M [D1]
        rows = np.broadcast_to(np.arange(lay.height)[:, None], i.shape)
        e[rows[write], x[write]] = values[write]
        return e
