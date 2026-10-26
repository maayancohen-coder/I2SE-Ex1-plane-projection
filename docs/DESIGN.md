# Design

The object-oriented design of the program: modules, classes, their responsibilities and how they work together.
Requirements are in the [SRS](SRS.md), the algorithm in [ALGORITHM.md](ALGORITHM.md).

## Overview

```
                         Ex0.py  (main)
     reads the input, runs the projection for every plane, writes the video, prints the timing
                            |
     +----------------------+----------------------+------------------------+
     |                      |                      |                        |
nrrd_reader.py          plane.py             projector.py           video_writer.py
  read_nrrd()             Plane (abstract)     Projector (abstract)   Normalizer
    -> Volume               Triangle             ReferenceProjector   VideoWriter
                            Trapezoid            FastProjector
                          parse_planes()
```

Data flow for one run:

```
file.nrrd --read_nrrd--> Volume
file.csv  --parse_planes--> [(line number, Plane or error), ...]
for every plane:   Projector.project(Volume, Plane) --> E  --Normalizer--> 8-bit frame
                   (invalid row or plane --> black frame + warning)
all frames --VideoWriter--> file.mp4
```

## Modules and classes

### `nrrd_reader.py`
| Name | Responsibility |
|------|----------------|
| `Volume` | Holds the 3D matrix `M` (a numpy array indexed `M[x][y][z]`) and its value type. Read-only after creation. |
| `read_nrrd(path) -> Volume` | Parses the NRRD header and data (raw or gzip). Raises `VolumeError` for every file error (FR-2, FR-3). |

### `plane.py`
| Name | Responsibility |
|------|----------------|
| `Plane` (abstract) | A plane as two legs: `start1 -> b` and `start2 -> c`. Offers `start1`, `start2`, `b`, `c`, and `validate()`. |
| `Triangle(a, b, c)` | `start1 = start2 = a`. Valid if isosceles within `TOLERANCE` and not degenerate [D9]. |
| `Trapezoid(a1, a2, b, c)` | `start1 = a'`, `start2 = a''`. Valid if the legs are equal within `TOLERANCE`, `|a'a''| <= |bc|`, and the four points are on one plane [D9]. |
| `parse_planes(path)` | Reads the CSV file [D10]. Returns, for every non-comment line, its line number and either a `Plane` or the reason it is invalid. Raises `PlaneFileError` if the file is missing or has no planes. |

### `projector.py`
| Name | Responsibility |
|------|----------------|
| `round_half_up(v)`, `sample(volume, p)` | The helpers of the algorithm [D1, D2]. |
| `Projector` (abstract) | Interface: `project(volume, plane) -> E`. |
| `ReferenceProjector` | A direct translation of [ALGORITHM.md](ALGORITHM.md) with plain loops. Simple, slow, used as the reference in tests. |
| `FastProjector` | The same algorithm, computed for all pixels at once with numpy (NFR-1). Must return exactly the same `E` as the reference. |

### `video_writer.py`
| Name | Responsibility |
|------|----------------|
| `Normalizer` | Built once from the whole volume; maps values to `0..255` with percentiles and the fallback [D8]. |
| `VideoWriter` | Pads every frame to one even size, centred on black [D11], and writes the mp4 at 10 fps (FR-10). Uses `imageio` with `imageio-ffmpeg`, which brings its own ffmpeg for Windows, macOS and Linux (NFR-6). |

### `Ex0.py`
Checks the arguments (FR-1), connects the modules, turns every error into a clear message without a traceback (NFR-2), and prints the timing summary (FR-11).

### Errors
All expected errors are exceptions of the program, so `Ex0.py` can catch them in one place:

```
ProjectionError
 +-- VolumeError      (NRRD file problems)
 +-- PlaneFileError   (CSV file missing or without planes)
```
An invalid row or an invalid plane is not an exception for the whole run: `parse_planes` reports it for that line only [D9].

## Design principles

| Principle | Where |
|-----------|-------|
| **Single responsibility** | Each module does one job: read, describe the plane, project, write (NFR-4). |
| **Polymorphism** | The projector never asks "triangle or trapezoid?". It only uses `start1`, `start2`, `b`, `c`, so one algorithm serves both shapes, as the assignment says ("the same algorithm holds"). |
| **Strategy** | `ReferenceProjector` and `FastProjector` implement the same interface and can replace each other. This makes it possible to test the fast one against the simple one. |
| **Fail clearly** | File errors stop the run with a message; row errors only affect their own frame [D9]. |
| **No hidden state** | `Volume` and the planes do not change after they are created, so the same objects can be used for many projections. |
