# Software Requirements Specification (SRS)

## 1. Introduction
### 1.1 Purpose
### 1.2 Scope
### 1.3 Definitions
- Volume `M`, voxel, plane, isosceles triangle / trapezoid, output image `E`.

## 2. Overall description
### 2.1 Inputs
- NRRD file
- CSV file: format TBD (one plane per row? 9 or 12 numbers?)
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
| 2 | `x` is not an integer: round or floor? Width of `E`? | Round to the nearest integer; exact halves round up (2.5 -> 3). The width of `E` is `Dbc + 1`. Same rounding rule is used for `p` (decision 1). | Keeps every row centred. One consistent rounding rule across the system. The last row reaches column `Dbc`, so `Dbc + 1` columns are needed. Note: Python's `round()` rounds halves to even, so it is not used. |
| 3 | `Dab`, `Dbc` are not integers: exact size of `E`? | Height: `floor(Dab) + 1` rows (see decision 4). Width: `round(Dbc) + 1` columns. | The problem statement projects points "within the triangle". Rows are sampled at distances `0 .. floor(Dab)` from `a`, so `a1` and `a2` never pass `b` and `c`, and every pixel is inside the triangle (the original loop `y < Dab` can step past `b` in the last row). The width follows decision 2. |
| 4 | The apex `a` is never sampled (step before sample): keep or fix? | Fix: sample first, then step. Row `y` is at distance `y` from `a`, for `y = 0 .. floor(Dab)`. | The problem statement projects every point "within the triangle", including the apex `a`. Sampling at distances `0 .. floor(Dab)` includes both the apex and (when `Dab` is an integer) the base `bc`. The row at `y = 0` has `d12 = 0`, see decision 5. |
| 5 | `d12 = 0`: division by zero | | |
| 6 | Index coordinates or physical (mm) coordinates? | | |
| 7 | Orientation of `E`: `E[x][y]` vs `E[y][x]` | | |
| 8 | 16/32-bit values: normalisation to 8-bit for video | | |
| 9 | Invalid input: not isosceles, collinear points, bad CSV | | |
