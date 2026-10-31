"""
Experiment (docs/EXPERIMENT.md): how fast is the projection on the course volumes,
and how much would trilinear interpolation change the images?

For every NRRD file in the data folder:
  1. write 100 sweep planes to experiments/planes/<name>.csv
  2. speed: FastProjector on all 100 planes, ReferenceProjector on 3 planes
  3. quality: nearest voxel (our choice, SRS decision 1) vs trilinear on the same planes
  4. a side-by-side image nearest | trilinear in docs/media/
  5. the demo video, made with the required command:  python Ex0.py file.nrrd file.csv file.mp4

The results are printed and saved in experiments/results.md.

Usage:
    python experiments/run_experiment.py [data folder]
"""
import platform
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from projection.nrrd_reader import read_nrrd                                    # noqa: E402
from projection.plane import EPSILON, Plane, Triangle, parse_planes             # noqa: E402
from projection.projector import FastProjector, Layout, Projector, ReferenceProjector   # noqa: E402
from projection.video_writer import Normalizer                                  # noqa: E402

PLANES = 100            # planes per volume
REFERENCE_PLANES = 3    # the loop version is slow, so it gets fewer planes
PLANES_DIR = ROOT / "experiments" / "planes"
MEDIA_DIR = ROOT / "docs" / "media"
RESULTS = ROOT / "experiments" / "results.md"


def sweep_planes(shape, n):
    """n isosceles triangles that cross the whole volume, tilted a little more each time."""
    sx, sy, sz = shape
    planes = []
    for t in np.linspace(0, 1, n):
        z_top, z_bottom = t * (sz - 1), (1 - t) * (sz - 1)
        # b and c are mirror images around x = sx / 2, so the triangle is isosceles
        planes.append(Triangle((sx / 2, 0, z_top), (0, sy - 1, z_bottom), (sx, sy - 1, z_bottom)))
    return planes


def write_csv(path, planes):
    lines = [f"# {len(planes)} sweep planes made by experiments/run_experiment.py",
             "# ax,ay,az,bx,by,bz,cx,cy,cz"]
    for plane in planes:
        lines.append(",".join(f"{v:.4f}" for v in [*plane.start1, *plane.b, *plane.c]))
    path.write_text("\n".join(lines) + "\n")


class TrilinearProjector(Projector):
    """The same sample points as FastProjector, but each value is interpolated
    from the 8 surrounding voxels instead of taken from the nearest one.

    Used only in this experiment, to measure what SRS decision 1 (nearest voxel) costs.
    A point is inside M under the same rule as in FastProjector, so both images cover the same pixels.
    """

    def project(self, volume, plane: Plane) -> np.ndarray:
        m = volume.data
        lay = Layout.of(plane)
        e = np.zeros((lay.height, lay.width), dtype=np.float64)

        y = np.arange(lay.height, dtype=float)[:, None]
        a1 = lay.start1 + y * lay.v_ab
        a2 = lay.start2 + y * lay.v_ac
        d = a2 - a1
        d12 = np.sqrt(d[:, 0] * d[:, 0] + d[:, 1] * d[:, 1] + d[:, 2] * d[:, 2])
        single = d12 < EPSILON
        d12 = np.where(single, 0.0, d12)
        dp = np.where(single[:, None], 0.0, d / np.where(single, 1.0, d12)[:, None])
        count = np.floor(d12).astype(np.int64) + 1
        x1 = np.arange(count.max(), dtype=float)[None, :]
        used = x1 < count[:, None]

        p = [a1[:, c:c + 1] + x1 * dp[:, c:c + 1] for c in range(3)]      # real coordinates
        x = np.floor(lay.dbc / 2 - d12[:, None] / 2 + x1 + 0.5).astype(np.int64)

        inside = used.copy()
        for c, s in enumerate(m.shape):
            inside &= (p[c] >= -0.5) & (p[c] < s - 0.5)                  # same rule as the nearest voxel
        write = used & (x >= 0) & (x < lay.width)

        # corner voxel and fraction along each axis, clamped to the volume
        lo, frac = [], []
        for c, s in enumerate(m.shape):
            q = np.clip(p[c][inside], 0, s - 1)
            i0 = np.minimum(np.floor(q).astype(np.int64), s - 2) if s > 1 else np.zeros(q.shape, np.int64)
            lo.append(i0)
            frac.append(q - i0 if s > 1 else np.zeros(q.shape))
        values = np.zeros(used.shape, dtype=np.float64)
        total = np.zeros(lo[0].shape)
        for di in (0, 1):
            for dj in (0, 1):
                for dk in (0, 1):
                    w = ((frac[0] if di else 1 - frac[0]) * (frac[1] if dj else 1 - frac[1])
                         * (frac[2] if dk else 1 - frac[2]))
                    idx = [np.minimum(lo[c] + o, m.shape[c] - 1) for c, o in enumerate((di, dj, dk))]
                    total += w * m[idx[0], idx[1], idx[2]]
        values[inside] = total

        rows = np.broadcast_to(np.arange(lay.height)[:, None], used.shape)
        e[rows[write], x[write]] = values[write]
        return e


def fps(projector, volume, planes):
    projector.project(volume, planes[0])                     # warm-up
    start = time.perf_counter()
    for plane in planes:
        projector.project(volume, plane)
    return len(planes) / (time.perf_counter() - start)


def compare(volume, planes, normalizer):
    """Mean absolute difference (grey levels 0..255) and PSNR between nearest and trilinear."""
    fast, tri = FastProjector(), TrilinearProjector()
    diffs, sq = [], []
    for plane in planes:
        a = normalizer.to_uint8(fast.project(volume, plane)).astype(np.float64)
        b = normalizer.to_uint8(tri.project(volume, plane)).astype(np.float64)
        diffs.append(np.abs(a - b).mean())
        sq.append(((a - b) ** 2).mean())
    mse = float(np.mean(sq))
    psnr = float("inf") if mse == 0 else 10 * np.log10(255 ** 2 / mse)
    return float(np.mean(diffs)), psnr


def side_by_side(volume, plane, normalizer, path):
    import imageio.v2 as imageio
    a = normalizer.to_uint8(FastProjector().project(volume, plane))
    b = normalizer.to_uint8(TrilinearProjector().project(volume, plane))
    gap = np.full((a.shape[0], 8), 255, dtype=np.uint8)
    imageio.imwrite(path, np.hstack([a, gap, b]))


def run_demo(nrrd, csv, mp4):
    result = subprocess.run([sys.executable, str(ROOT / "Ex0.py"), str(nrrd), str(csv), str(mp4)],
                            capture_output=True, text=True)
    print(result.stdout.rstrip())
    line = next((ln for ln in result.stdout.splitlines() if ln.startswith("Projected")), "")
    return line.split("(")[-1].rstrip(")") if "fps" in line else "failed"


def main(argv):
    data_dir = Path(argv[1]) if len(argv) > 1 else ROOT / "data"
    files = sorted(data_dir.glob("*.nrrd"))
    if not files:
        print(f"No NRRD files in {data_dir}")
        return 1
    PLANES_DIR.mkdir(parents=True, exist_ok=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    machine = f"{platform.system()} {platform.release()}, {platform.processor() or platform.machine()}, " \
              f"Python {platform.python_version()}, numpy {np.__version__}"
    rows = []
    for nrrd in files:
        name = nrrd.stem
        volume = read_nrrd(nrrd)
        planes = sweep_planes(volume.shape, PLANES)
        csv = PLANES_DIR / f"{name}.csv"
        write_csv(csv, planes)
        planes = [row.plane for row in parse_planes(csv)]       # exactly the planes in the file
        normalizer = Normalizer(volume)
        sx, sy, sz = volume.shape
        print(f"\n== {name}: {sx} x {sy} x {sz}, {volume.dtype}")

        fast = fps(FastProjector(), volume, planes)
        reference = fps(ReferenceProjector(), volume, planes[:REFERENCE_PLANES])
        trilinear = fps(TrilinearProjector(), volume, planes)
        mad, psnr = compare(volume, planes, normalizer)
        side_by_side(volume, planes[PLANES * 3 // 10], normalizer, MEDIA_DIR / f"{name}_nearest_vs_trilinear.png")
        demo = run_demo(nrrd, csv, MEDIA_DIR / f"{name}.mp4")

        row = (name, f"{sx}x{sy}x{sz}", str(volume.dtype), f"{fast:.0f}", f"{reference:.2f}",
               f"{fast / reference:.0f}x", f"{trilinear:.0f}", f"{mad:.2f}", f"{psnr:.1f}", demo)
        print(" | ".join(row))
        rows.append(row)

    header = ("Volume", "Size", "Type", "Fast fps", "Reference fps", "Speed-up",
              "Trilinear fps", "Mean diff (0-255)", "PSNR (dB)", "Ex0.py")
    table = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    table += ["| " + " | ".join(r) + " |" for r in rows]
    RESULTS.write_text(f"# Results\n\nMachine: {machine}\n\n"
                       f"{PLANES} sweep planes per volume (experiments/planes/), "
                       f"reference on the first {REFERENCE_PLANES}.\n\n" + "\n".join(table) + "\n")
    print(f"\nMachine: {machine}\nSaved {RESULTS.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
