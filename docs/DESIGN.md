# Design

The object-oriented design of the program: modules, classes, their responsibilities and how they work together.
Requirements are in the [SRS](SRS.md), the algorithm in [ALGORITHM.md](ALGORITHM.md).

## Overview

```
          Ex0.py (command line)                 gui.py (window)
                     \                              /
                      +---- pipeline.run() -------+
     reads the input, runs the projection for every plane, writes the video, reports the timing
                            |
     +----------------------+----------------------+------------------------+
     |                      |                      |                        |
nrrd_reader.py          plane.py             projector.py           video_writer.py
  read_nrrd()             Plane (abstract)     Projector (abstract)   Normalizer
    -> Volume               Triangle             ReferenceProjector   ErrorFrame
                            Trapezoid            FastProjector        VideoWriter
                          parse_planes()
```

Data flow for one run:

```
file.nrrd --read_nrrd--> Volume
file.csv  --parse_planes--> [(line number, Plane or error), ...]
for every plane:   Projector.project(Volume, Plane) --> E  --Normalizer--> 8-bit frame
                   (invalid row or plane --> ErrorFrame + warning)
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
| `ErrorFrame` | The frame of an invalid CSV row: black, with a red X, the line number and the reason (Q&A 3b). It is drawn at the final frame size when the video is written (with Pillow). |
| `VideoWriter` | Pads every frame to one even size, centred on black [D11], and writes the mp4 at 10 fps (FR-10). Uses `imageio` with `imageio-ffmpeg`, which brings its own ffmpeg for Windows, macOS and Linux (NFR-6). |

### `pipeline.py`
| Name | Responsibility |
|------|----------------|
| `run(nrrd, csv, mp4, log=print, on_frame=None) -> Summary` | The whole program in one function: reads, projects every plane, writes the video and reports the timing (FR-11). `log` receives every message; `on_frame(index, total, frame)` is called after each frame. Both are callbacks, so the same code serves the command line and the window. |
| `Summary` | What one run produced: frames, valid planes, average time, frame size. |

### `Ex0.py`
The command line of the assignment. Checks the arguments (FR-1), calls `pipeline.run` with `log=print`, and turns every error into a clear message without a traceback (NFR-2).

### `gui.py` and `preview.py`
An optional window on top of the same code (not required by the assignment).

| Name | Responsibility |
|------|----------------|
| `ProjectionApp` (`gui.py`) | The tkinter window: file choice, Run, progress bar, live preview, a slider and Play over the frames, the log, and "Explore a plane". |
| `explore_plane(shape, axis, position, tilt, top)` (`preview.py`) | Builds a valid isosceles triangle (`top = 0`) or trapezoid across the volume from the explore sliders. |
| `to_preview`, `csv_line`, `default_output` (`preview.py`) | Scale a frame for the preview, write a plane as a CSV line, suggest the output name. |

`preview.py` has no tkinter code, so it is tested everywhere, including GitHub Actions.
The projection runs in a worker thread; the worker never touches the window, it only puts messages in a
`queue.Queue` that the window reads every 30 ms (tkinter is not thread safe). This is the producer-consumer pattern.

### `errors.py`
All expected errors are exceptions of the program, so `Ex0.py` can catch them in one place:

```
ProjectionError        stops the run; Ex0.py prints "Error: ..." without a traceback
 +-- VolumeError       NRRD file problems
 +-- PlaneFileError    CSV file missing, unreadable or without planes
 +-- OutputError       the video cannot be written

PlaneError             (a ValueError) one invalid plane: raised by validate(),
                       caught by parse_planes for that line only -> error frame [D9]
```

## Tests

The tests mirror the modules (see [TESTING.md](TESTING.md)):

```
tests/
  test_plane.py         -> plane.py
  test_nrrd_reader.py   -> nrrd_reader.py
  test_projector.py     -> projector.py      (every test on both projectors)
  test_video_writer.py  -> video_writer.py
  test_demo.py          -> Ex0.py, run as a separate process
  test_pipeline.py      -> pipeline.py       (messages and frame callback)
  test_preview.py       -> preview.py        (explore planes, preview images)
  test_user_data.py     -> the whole program on real files (pytest -m data --nrrd ...)
  nrrd_files.py         helper: writes small valid and broken NRRD files
  conftest.py           pytest options --nrrd and --csv
  data/*.csv            planes for the tests
```

## Design principles

| Principle | Where |
|-----------|-------|
| **Single responsibility** | Each module does one job: read, describe the plane, project, write (NFR-4). |
| **Polymorphism** | The projector never asks "triangle or trapezoid?". It only uses `start1`, `start2`, `b`, `c`, so one algorithm serves both shapes, as the assignment says ("the same algorithm holds"). |
| **Strategy** | `ReferenceProjector` and `FastProjector` implement the same interface and can replace each other. This makes it possible to test the fast one against the simple one. |
| **Fail clearly** | File errors stop the run with a message; row errors only affect their own frame [D9]. |
| **Separate the interface from the logic** | `Ex0.py` and `gui.py` only collect input and show output; both call `pipeline.run`. A new interface needs no change in the algorithm. |
| **No hidden state** | `Volume` and the planes do not change after they are created, so the same objects can be used for many projections. |
