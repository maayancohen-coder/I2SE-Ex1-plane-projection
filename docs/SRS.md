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
| 1 | `p` is not an integer: nearest voxel or trilinear interpolation? | | |
| 2 | `x` is not an integer: round or floor? Width of `E`? | | |
| 3 | `Dab`, `Dbc` are not integers: exact size of `E`? | | |
| 4 | The apex `a` is never sampled (step before sample): keep or fix? | | |
| 5 | `d12 = 0`: division by zero | | |
| 6 | Index coordinates or physical (mm) coordinates? | | |
| 7 | Orientation of `E`: `E[x][y]` vs `E[y][x]` | | |
| 8 | 16/32-bit values: normalisation to 8-bit for video | | |
| 9 | Invalid input: not isosceles, collinear points, bad CSV | | |
