"""Helpers for the tests: write small NRRD files (valid and broken) into a temporary folder."""
import gzip

import numpy as np


def write_nrrd(path, volume, nrrd_type=None, encoding="gzip", header_extra="", header=None, data=None):
    """Write volume (indexed [x][y][z]) as an NRRD file.

    header and data can be given to create broken files on purpose.
    """
    volume = np.asarray(volume)
    if header is None:
        nrrd_type = nrrd_type or {"u1": "uint8", "u2": "uint16", "i2": "short", "u4": "uint32"}[volume.dtype.str[1:]]
        sx, sy, sz = volume.shape
        header = (f"NRRD0004\n# test file\ntype: {nrrd_type}\ndimension: 3\nsizes: {sx} {sy} {sz}\n"
                  f"endian: little\nencoding: {encoding}\n{header_extra}")
    if data is None:
        data = volume.astype(volume.dtype.newbyteorder("<")).transpose(2, 1, 0).tobytes()   # x fastest
        if encoding == "gzip":
            data = gzip.compress(data)
    with open(path, "wb") as f:
        f.write(header.encode("ascii") + b"\n" + data)
    return path


def numbered_volume(shape=(4, 5, 6), dtype=np.uint16):
    """A volume where every voxel has a different value: v = x + 10*y + 100*z."""
    x, y, z = np.indices(shape)
    return (x + 10 * y + 100 * z).astype(dtype)
