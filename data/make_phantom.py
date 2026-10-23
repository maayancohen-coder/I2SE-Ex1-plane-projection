"""
make_phantom.py - Generate a synthetic 3D test volume ("phantom") as an NRRD file.

The volume contains three objects with known geometry and distinct intensities:
  1. A hollow spherical shell        (value 80)   - every plane cut is a ring / circle
  2. A trefoil knot tube             (value 255)  - plane cuts give several separate blobs
  3. A solid cube at the center      (value 160)  - plane cuts give polygons (3-6 sides)

Because the geometry is analytic, the expected output of any plane projection
can be predicted, which makes this file useful for testing.

Usage:
    python make_phantom.py                     # writes phantom_knot.nrrd (200^3)
    python make_phantom.py out.nrrd 256        # custom file name and size

Requirements: numpy, scipy   (pip install numpy scipy)
"""

import gzip
import sys

import numpy as np
from scipy.ndimage import distance_transform_edt


def make_shell(n, center, r_outer, thickness):
    """Boolean mask of a hollow sphere."""
    z, y, x = np.ogrid[:n, :n, :n]
    dist = np.sqrt((x - center) ** 2 + (y - center) ** 2 + (z - center) ** 2)
    return (dist <= r_outer) & (dist >= r_outer - thickness)


def make_cube(n, center, half_side):
    """Boolean mask of an axis-aligned solid cube."""
    lo, hi = int(center - half_side), int(center + half_side)
    mask = np.zeros((n, n, n), dtype=bool)
    mask[lo:hi, lo:hi, lo:hi] = True
    return mask


def make_trefoil(n, center, scale, tube_radius, samples=4000):
    """
    Boolean mask of a tube around a trefoil knot.

    Parametric trefoil:
        x = sin(t) + 2 sin(2t)
        y = cos(t) - 2 cos(2t)
        z = -sin(3t)
    Method: mark every voxel the curve passes through, then use a Euclidean
    distance transform to get each voxel's distance from the curve.
    """
    t = np.linspace(0, 2 * np.pi, samples, endpoint=False)
    cx = np.sin(t) + 2 * np.sin(2 * t)
    cy = np.cos(t) - 2 * np.cos(2 * t)
    cz = -np.sin(3 * t)

    # map curve coordinates (range about [-3, 3]) into voxel indices
    ix = np.clip(np.round(center + scale * cx).astype(int), 0, n - 1)
    iy = np.clip(np.round(center + scale * cy).astype(int), 0, n - 1)
    iz = np.clip(np.round(center + scale * cz * 1.5).astype(int), 0, n - 1)

    not_curve = np.ones((n, n, n), dtype=bool)
    not_curve[iz, iy, ix] = False          # numpy order is [z][y][x]
    dist = distance_transform_edt(not_curve)
    return dist <= tube_radius


def write_nrrd(path, volume, spacing=(1.0, 1.0, 1.0)):
    """
    Minimal NRRD writer (uint8, gzip).
    The NRRD header is plain text, followed by a blank line, then the raw data.
    NRRD 'sizes' are listed fastest axis first (x y z); numpy C-order [z][y][x]
    already stores x as the fastest-changing index, so no transpose is needed.
    """
    nz, ny, nx = volume.shape
    header = (
        "NRRD0004\n"
        "# Synthetic phantom: spherical shell + trefoil knot + cube\n"
        "type: uint8\n"
        "dimension: 3\n"
        "space: left-posterior-superior\n"
        f"sizes: {nx} {ny} {nz}\n"
        f"space directions: ({spacing[0]},0,0) (0,{spacing[1]},0) (0,0,{spacing[2]})\n"
        "kinds: domain domain domain\n"
        "endian: little\n"
        "encoding: gzip\n"
        f"space origin: ({-nx * spacing[0] / 2},{-ny * spacing[1] / 2},{-nz * spacing[2] / 2})\n"
        "\n"
    )
    with open(path, "wb") as f:
        f.write(header.encode("ascii"))
        f.write(gzip.compress(volume.astype(np.uint8).tobytes(order="C")))


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "phantom_knot.nrrd"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 200
    c = n / 2

    volume = np.zeros((n, n, n), dtype=np.uint8)
    # later assignments overwrite earlier ones where objects overlap
    volume[make_shell(n, c, r_outer=0.47 * n, thickness=0.03 * n)] = 80
    volume[make_cube(n, c, half_side=0.07 * n)] = 160
    volume[make_trefoil(n, c, scale=0.12 * n, tube_radius=0.04 * n)] = 255

    write_nrrd(out_path, volume)
    print(f"Wrote {out_path}: {n}x{n}x{n} uint8, "
          f"{np.count_nonzero(volume)} non-zero voxels")


if __name__ == "__main__":
    main()
