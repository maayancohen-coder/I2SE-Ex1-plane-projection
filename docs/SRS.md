# Software Requirements Specification (SRS)

## 1. Introduction
### 1.1 Purpose
This document specifies the requirements and the design decisions for a program that projects a plane of a 3D volume into a 2D image, and writes a sequence of such images as a video. It is intended for the developer, the testers and the course staff.

### 1.2 Scope
The scope (in scope, out of scope and constraints) is defined in the [README](../README.md). This document refines it into numbered requirements (sections 3, 4) and closes the open points of the assignment (section 5).

### 1.3 Definitions
- **Volume `M`**: a 3D matrix of voxel values, read from an NRRD file, of size `sx * sy * sz`.
- **Voxel**: one cell of `M` (a 3D pixel), accessed by integer indices `M[x][y][z]`.
- **Plane**: given by 3 points (isosceles triangle `a, b, c` with `|ab| = |ac|`) or 4 points (isosceles trapezoid `a', a'', b, c`).
- **`Dab`, `Dbc`**: the length of a leg and the length of the base.
- **`a1`, `a2`**: the two points that move down the legs, one step per row.
- **`d12`**: the distance between `a1` and `a2` in the current row.
- **Output image `E`**: the 2D projection of one plane.
- **Frame**: one image of the output video; one frame per plane.
- `EPSILON = 1e-9`: tolerance for comparing floating-point values to zero.
- `TOLERANCE = 1e-3`: allowed difference between `|ab|` and `|ac|` (in voxels) for user input.
## 2. Overall description
### 2.1 Inputs
- NRRD file
- CSV file: a list of planes, format defined in decision 10.
### 2.2 Outputs
- mp4 video, one frame per plane

## 3. Functional requirements 

## 4. Non-functional requirements
- Performance: >= 30 fps on a 500^3 volume (target 100 fps).
- Robustness: invalid input is reported, never crashes.

## 5. Design decisions (closing the ambiguities)
| # | Question | Decision | Reason |
|---|----------|----------|--------|
| 1 | `p` is not an integer: nearest voxel or trilinear interpolation? | Nearest neighbour: round each coordinate of `p` to the nearest integer. | Fastest option (1 memory access per pixel), needed for the 30 fps requirement. Keeps original voxel values, which makes testing exact. Matches `v = M[p]` in the given algorithm. The visual difference is expected to be small; this will be checked in the experiment. |
| 2 | `x` is not an integer: round or floor? Width of `E`? | Round to the nearest integer; exact halves round up (2.5 -> 3). The width of `E` is `round(Dbc) + 1` (see decision 3). Same rounding rule is used for `p` (decision 1). | Keeps every row centred. One consistent rounding rule across the system. The last row reaches column `Dbc`, so `Dbc + 1` columns are needed. Note: Python's `round()` rounds halves to even, so it is not used. |
| 3 | `Dab`, `Dbc` are not integers: exact size of `E`? | Height: `floor(Dab) + 1` rows (see decision 4). Width: `round(Dbc) + 1` columns. | The problem statement projects points "within the triangle". Rows are sampled at distances `0 .. floor(Dab)` from `a`, so `a1` and `a2` never pass `b` and `c`, and every pixel is inside the triangle (the original loop `y < Dab` can step past `b` in the last row). The width follows decision 2. |
| 4 | The apex `a` is never sampled (step before sample): keep or fix? | Fix: sample first, then step. Row `y` is at distance `y` from `a`, for `y = 0 .. floor(Dab)`. | The problem statement projects every point "within the triangle", including the apex `a`. Sampling at distances `0 .. floor(Dab)` includes both the apex and (when `Dab` is an integer) the base `bc`. The row at `y = 0` has `d12 = 0`, see decision 5. |
| 5 | `d12 = 0`: division by zero | Special case: if `d12 < EPSILON`, the row is a single point. Sample `M` at `a1`, write one pixel at the centre of the row, and do not compute `dp`. | Happens in the first row of a triangle (`a1 = a2 = a`, see decision 4). Skipping the row would drop the apex again. `EPSILON` is used instead of `== 0` because of floating-point error. A degenerate triangle (`b = c`) is rejected as invalid input (decision 9). |
| 6 | Index coordinates or physical (mm) coordinates? | Index coordinates: the points in the CSV are voxel indices in `M`, and every step is one voxel. Voxel spacing in the NRRD header is ignored. | The assignment defines the problem in index space (`M[x][y][z]`, `0 <= x < sx`). Simpler and faster: no conversion per sample. Known limitation: for volumes with non-uniform spacing (e.g. MRHead 1 x 1 x 1.3 mm) the image is slightly distorted along one axis. |
| 7 | Orientation of `E`: `E[x][y]` vs `E[y][x]` | `E` is stored row-major as `E[y][x]` (row, then column). Row 0 is the apex `a` (top), column 0 is on the `b` side (left), the last column is on the `c` side (right). | This is the standard image layout in numpy, video libraries and 2D arrays in general, so frames can be written without transposing. Storing `E[x][y]` as written in the assignment would produce rotated and mirrored frames. Fixing the sides of `a`, `b`, `c` makes the output predictable and testable. |
| 8 | 16/32-bit values: normalisation to 8-bit for video | uint8 volumes are used as is. Other types: compute once, on the whole volume, the 0.5 and 99.5 percentiles (`lo`, `hi`), map `[lo, hi]` linearly to `[0, 255]` and clip values outside. The same mapping is used for all frames. | One mapping for the whole volume keeps the same tissue at the same brightness in every frame (per-frame normalisation would flicker). Percentiles instead of min/max ignore a few extreme voxels: in MRHead the max is 279 but 99.5% of voxels are below 141, so min/max would make the image dark. Computed once at load time, so it does not affect fps. |
| 9 | Invalid input: not isosceles, collinear points, bad CSV | File errors (missing or unreadable NRRD/CSV, not 3D, size out of range, unsupported type): stop with a clear error message. Row errors (wrong number of values, non-numeric value) and invalid planes (`abs(|ab| - |ac|) > TOLERANCE`, collinear or identical points): write a black frame and print a warning with the row number. A plane outside the volume is valid and gives a black frame. | Without a valid volume nothing can be computed. One bad row should not cancel the whole video, and writing a black frame keeps frame `i` aligned with CSV row `i`. User input needs a looser tolerance than `EPSILON`. |
| 10 | CSV format | One plane per line, comma-separated numbers (integers or decimals) in index coordinates (decision 6). 9 values = triangle `a, b, c` (apex, then base from left to right). 12 values = trapezoid `a', a'', b, c` (top edge left to right, then base left to right; legs are `a'->b` and `a''->c`). Empty lines and lines starting with `#` are ignored and do not produce frames. No header line. | The assignment only says "3 or 4 points". A fixed point order is needed to know which point is the apex and which side is left (decision 7). Comments make test files readable. Frame `i` in the video is the `i`-th non-comment line. |
| 11 | Frames have different sizes, but a video needs one frame size | Before writing the video, compute the size of `E` for every plane. The frame size is the maximum height and maximum width, rounded up to even numbers. Each `E` is placed in the centre of a black frame of that size. Images are not scaled. | Video files require one fixed frame size (and even dimensions for mp4/H.264). Padding instead of scaling keeps one pixel = one voxel in every frame, so sizes can be compared between frames, and no extra computation is needed. |