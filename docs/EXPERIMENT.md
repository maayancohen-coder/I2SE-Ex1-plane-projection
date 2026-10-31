# Experiment

Two questions about the choices in the SRS:

1. **Speed (NFR-1):** is the projection fast enough for at least 30 planes per second, also on the largest volume (croissant, 500³)?
2. **Sampling (SRS decision 1):** we take the nearest voxel. How different would the images be with trilinear interpolation, and what would it cost?

## Setup

| | |
|---|---|
| Script | [`experiments/run_experiment.py`](../experiments/run_experiment.py) |
| Run | `python experiments/run_experiment.py` (all `.nrrd` files in `data/`) |
| Machine | Windows 11 laptop, on mains power, power mode "Best performance"; Intel 12th generation laptop CPU (Intel64 Family 6 Model 154), Python 3.15.0, numpy 2.5.4 |
| Volumes | the five course volumes, see [`data/README.md`](../data/README.md) |
| Planes | 100 isosceles triangles per volume that sweep through the whole volume, tilting a little more each time. Saved in [`experiments/planes/`](../experiments/planes/), so the run can be repeated on the same planes |
| Raw results | [`experiments/results.md`](../experiments/results.md) |

What is measured, for each volume:

- **Fast fps:** `FastProjector` (numpy and parallel threads, the one `Ex0.py` uses) on all 100 planes, after one warm-up plane.
- **Reference fps:** `ReferenceProjector` (plain loops, a direct translation of [ALGORITHM.md](ALGORITHM.md)) on the first 3 planes, since it is slow.
- **Trilinear fps:** `TrilinearProjector`, which exists only in the experiment script. It visits exactly the same sample points as `FastProjector`, but each value is a weighted average of the 8 surrounding voxels instead of the nearest one.
- **Mean diff and PSNR:** both images are mapped to 0..255 with the same `Normalizer` as the video, then compared pixel by pixel over all 100 planes. PSNR above 30 dB is usually considered very close.
- **Ex0.py:** the demo video made with the required command `python Ex0.py file.nrrd file.csv file.mp4`, and the fps that `Ex0.py` printed.

## Results

| Volume | Size | Type | Fast fps | Reference fps | Speed-up | Trilinear fps | Mean diff (0-255) | PSNR (dB) | Ex0.py |
|---|---|---|---|---|---|---|---|---|---|
| biscuit_cake | 256x256x130 | uint16 | 410 | 8.84 | 46x | 127 | 1.83 | 34.9 | 406 fps |
| croissant | 500x500x500 | uint8 | 161 | 2.46 | 65x | 18 | 2.35 | 31.0 | 142 fps |
| MRHead | 256x256x130 | int16 | 649 | 11.62 | 56x | 197 | 3.10 | 31.5 | 414 fps |
| onion | 256x256x130 | uint8 | 662 | 12.66 | 52x | 188 | 2.58 | 32.5 | 429 fps |
| swiss_roll | 256x256x130 | uint32 | 637 | 11.78 | 54x | 178 | 2.54 | 31.2 | 397 fps |

### Nearest voxel (left) vs trilinear (right)

The plane at 30% of the sweep, from each volume.

| | |
|---|---|
| MRHead ![MRHead](media/MRHead_nearest_vs_trilinear.png) | onion ![onion](media/onion_nearest_vs_trilinear.png) |
| croissant ![croissant](media/croissant_nearest_vs_trilinear.png) | swiss_roll ![swiss_roll](media/swiss_roll_nearest_vs_trilinear.png) |
| biscuit_cake ![biscuit_cake](media/biscuit_cake_nearest_vs_trilinear.png) | |

### Videos

The output of `Ex0.py` on the 100 sweep planes of each volume (10 seconds at 10 fps):
[MRHead](media/MRHead.mp4) ·
[onion](media/onion.mp4) ·
[croissant](media/croissant.mp4) ·
[swiss_roll](media/swiss_roll.mp4) ·
[biscuit_cake](media/biscuit_cake.mp4)

## Conclusions

1. **NFR-1 is met, including the target of 100 fps.** The slowest case is croissant (500³) at 161 fps,
   above both the required 30 and the expected 100. `Ex0.py` itself, which also counts the first, slower call,
   reached 142 fps. On the 256x256x130 volumes the projection runs at about 400–660 fps.
2. **How we got there (version history).** The first numpy version computed every row of `E` as long as the longest
   row and then dropped the unused samples. On croissant it reached only 52 fps in the first run of this experiment,
   below the target. Two changes in `FastProjector`, without changing the algorithm, raised it to 161 fps:
   - only the samples the algorithm really takes are computed (`count[y]` per row), about half the work for a triangle;
   - large planes are split into groups of rows that run in parallel threads on several CPU cores
     (numpy releases Python's lock during array operations, and each group writes to its own rows of `E`).
   The images are bit for bit the same as before: the tests compare them with the reference (TESTING.md, level 3),
   and the demo videos and comparison images of the second run were byte-identical to the first.
3. **Vectorising was necessary.** The loop version reaches only about 9–13 fps on the small volumes and 2.5 fps on
   croissant, so it would fail NFR-1. The numpy version computes the same image 46–65 times faster.
4. **The cost depends mainly on the size of the plane.** Each pixel of E is one sample. Croissant's planes have
   about 4–5 times more pixels than those of the 256 volumes, and the fps drops about 4 times.
5. **Nearest voxel is a good choice (SRS decision 1).** The trilinear images differ by only 1.8–3.1 grey levels
   out of 255 on average (PSNR 31–35 dB). In the side-by-side images the anatomy and the structures look the same.
   Nearest voxel is also 3–9 times faster and never creates values that are not in the volume.
6. **What trilinear does better.** On fine, repeating structures (the onion layers and the croissant layers)
   nearest voxel shows small steps and a moiré pattern, and trilinear is smoother. Trilinear would pass NFR-1 on the
   256 volumes (127–197 fps), but not on croissant (18 fps; it is not parallelised, since it is only an experiment).
7. **The numbers depend on the state of the laptop.** A run on battery power, during the work, was 2–4 times slower
   for every projector, including the ones whose code did not change (reference 2.9 instead of 11.6 fps on MRHead).
   The table above is from a run on mains power with the "Best performance" power mode. Even on battery,
   croissant reached 113 fps.
