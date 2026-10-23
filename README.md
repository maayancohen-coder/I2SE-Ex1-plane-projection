# I2SE-Ex1-plane-projection

Plane projection of a 3D volume: extracting a 2D image from a 3D raster (NRRD) along an arbitrary plane.

Course: Introduction to Software Engineering (OOP, OOD), Ex1.

## Problem

Given a 3D matrix `M` of size `sx * sy * sz` (unsigned 8, 16 or 32 bit values, `1 <= sx, sy, sz < 2^10`)
and a plane `p`, compute the 2D image `E` of the projection of `p` in `M`.

The plane is given by three points `a, b, c` forming an isosceles triangle (`|ab| = |ac|`),
or by four points forming an isosceles trapezoid. Every point inside the triangle that lies inside `M`
is sampled into `E`; points outside `M` get the value 0.

## Scope

In scope:
- Reading 3D volumes in NRRD format (raw and gzip encodings).
- Projecting a plane given by 3 points (triangle) or 4 points (trapezoid).
- A demo that reads a list of planes from a CSV file and writes one video frame per plane.
- Runtime of at least 30 fps (target 100 fps) on a `500^3` volume.

Out of scope:
- A graphical user interface.
- File formats other than NRRD.

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
