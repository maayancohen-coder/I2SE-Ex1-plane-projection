"""The projection algorithm: sampling a plane of the volume into a 2D image E.

See docs/ALGORITHM.md. Decisions of the SRS are referred to as [D1] .. [D11].
"""
import math
import os
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
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
    """The same algorithm, computed for many pixels at once with numpy (NFR-1).

    Two speed-ups, both without changing the result:
    - only the samples that the algorithm really takes are computed (count[y] per row), not a
      full rectangle of height x longest row, which is about half the work for a triangle;
    - large planes are split into groups of rows that run in parallel threads. numpy releases
      Python's lock (GIL) during its array operations, so the threads use several CPU cores.
      The groups write to different rows of E, so they never touch the same pixel.
    Every arithmetic step is written in the same order as in ReferenceProjector,
    so both return exactly the same image.
    """

    MIN_SAMPLES_PER_THREAD = 50_000     # smaller planes are faster in one thread

    def __init__(self, threads: int = None, min_samples: int = MIN_SAMPLES_PER_THREAD):
        self.threads = threads or min(os.cpu_count() or 1, 8)
        self.min_samples = min_samples
        self._pool = None

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

        groups = min(self.threads, max(1, int(count.sum()) // self.min_samples))
        if groups == 1:
            self._rows(m, lay, e, a1, dp, d12, count, 0, lay.height)
            return e
        # split the rows into groups with about the same number of samples
        cuts = np.searchsorted(np.cumsum(count), np.linspace(0, count.sum(), groups + 1)[1:-1])
        bounds = [0, *cuts.tolist(), lay.height]
        if self._pool is None:
            self._pool = ThreadPoolExecutor(self.threads)
        jobs = [self._pool.submit(self._rows, m, lay, e, a1, dp, d12, count, r0, r1)
                for r0, r1 in zip(bounds[:-1], bounds[1:])]
        for job in jobs:
            job.result()                                        # also passes on any error
        return e

    @staticmethod
    def _rows(m, lay, e, a1, dp, d12, count, r0, r1):
        """Fill the rows r0 .. r1-1 of E."""
        if r1 <= r0:
            return
        n = count[r0:r1]
        r = np.repeat(np.arange(r0, r1), n)                     # the row of every sample
        x1 = (np.arange(r.size) - np.repeat(np.cumsum(n) - n, n)).astype(float)   # 0 .. count-1 in each row

        # p = a1 + x1 * dp for every sample, one coordinate at a time
        i = np.floor(a1[r, 0] + x1 * dp[r, 0] + 0.5).astype(np.int64)
        j = np.floor(a1[r, 1] + x1 * dp[r, 1] + 0.5).astype(np.int64)
        k = np.floor(a1[r, 2] + x1 * dp[r, 2] + 0.5).astype(np.int64)
        x = np.floor(lay.dbc / 2 - d12[r] / 2 + x1 + 0.5).astype(np.int64)

        sx, sy, sz = m.shape
        inside = (i >= 0) & (i < sx) & (j >= 0) & (j < sy) & (k >= 0) & (k < sz)
        write = (x >= 0) & (x < lay.width)

        values = np.zeros(r.size, dtype=m.dtype)
        values[inside] = m[i[inside], j[inside], k[inside]]    # nearest voxel, 0 outside M [D1]
        e[r[write], x[write]] = values[write]
