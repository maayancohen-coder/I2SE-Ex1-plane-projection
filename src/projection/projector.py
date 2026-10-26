"""The projection algorithm: sampling a plane of the volume into a 2D image E."""
import math

import numpy as np


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
