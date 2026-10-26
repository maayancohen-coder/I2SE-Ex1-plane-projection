# I2SE-Ex1-plane-projection

Plane projection of a 3D volume: extracting a 2D image from a 3D raster (NRRD) along an arbitrary plane.

- Course: Introduction to Software Engineering (OOP, OOD), Ex1.
- Authors: Maayan Cohen, Talya Elmaliah
- Status: in progress (requirements and design)

## Explainer video

A 65-second walkthrough of the algorithm on the MRHead volume: the triangle `a, b, c`,
the unit vectors, the row-by-row sweep, the centring formula and why the triangle is isosceles.

[![Explainer video](docs/media/explainer_preview.png)](docs/media/plane_projection_explainer.mp4)

Click the image to open the video ([docs/media/plane_projection_explainer.mp4](docs/media/plane_projection_explainer.mp4)).

## Problem

Given a 3D matrix `M` of size `sx * sy * sz` (unsigned 8, 16 or 32 bit values, `1 <= sx, sy, sz < 2^10`)
and a plane `p`, compute the 2D image `E` of the projection of `p` in `M`.

The plane is given by three points `a, b, c` forming an isosceles triangle (`|ab| = |ac|`),
or by four points forming an isosceles trapezoid. Every point inside the triangle that lies inside `M`
is sampled into `E`; points outside `M` get the value 0.

## Scope

In scope:
- Reading 3D volumes in NRRD format (raw and gzip encodings).
- Reading a list of planes from a CSV file and validating them.
- Projecting a plane given by 3 points (triangle) or 4 points (trapezoid).
- Writing the projected images as video frames, in the order of the CSV.
- Clear error messages for invalid input (missing files, bad CSV rows, invalid planes).

Out of scope:
- A graphical user interface (command line only).
- 3D rendering or display of the volume (use 3D Slicer for that).
- File formats other than NRRD (e.g. DICOM, NIfTI).
- Editing or writing volumes: the input file is read only.

## Constraints

| Constraint | Value | Source |
|------------|-------|--------|
| Volume size | `1 <= sx, sy, sz < 2^10` | Problem definition |
| Voxel values | unsigned 8, 16 or 32 bit | Problem definition |
| Performance | at least 30 fps on a `500^3` volume (target 100 fps) | Implementation requirements |
| Language | Python | Implementation requirements (Java, Python, C, C++) |
| Input format | NRRD | Data |
| Command line | `python Ex0.py file.nrrd file.csv file.mp4` | To Do, item 7 |

Note: the assignment specifies unsigned values, but the reference file `MRHead.nrrd` is signed 16 bit (`short`).
Signed 16-bit volumes are also supported; see [docs/SRS.md](docs/SRS.md).

See [docs/SRS.md](docs/SRS.md) for the full requirements and design decisions.

## Project structure

```
Ex0.py                  demo entry point
src/projection/         source code
tests/                  unit and integration tests
docs/                   SRS, algorithm, testing strategy, experiment
data/                   dataset description and phantom generator
```

## Setup

```
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
```

## Usage

```
python Ex0.py file.nrrd file.csv file.mp4
```

- `file.nrrd`: a 3D volume in NRRD format.
- `file.csv`: a list of planes, 3 or 4 points each (format defined in [docs/SRS.md](docs/SRS.md)).
- `file.mp4`: the output video, one frame per plane, in the order of the CSV.

## Data

The NRRD files are not stored in the repository because of their size.
See [data/README.md](data/README.md) for the dataset and where to get each file.
