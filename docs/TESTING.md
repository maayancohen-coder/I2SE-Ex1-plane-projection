# Testing strategy

This document describes how the program is tested, and which test covers which requirement of the [SRS](SRS.md).
Decisions are referred to as [D1] .. [D11] (SRS section 5).

## Tools
- **pytest**: all automated tests are in `tests/` and run with `pytest`.
- Tests are grouped by labels (markers), defined in `pytest.ini`:

| Label | What | Runs with |
|-------|------|-----------|
| (none) | fast tests, no large files needed | `pytest` |
| `slow` | performance and comparison on the course files `data/MRHead.nrrd`, `data/croissant.nrrd` | `pytest -m slow` |
| `data` | tests on real NRRD files: the files in `data/`, or any file given with `--nrrd` | `pytest -m data` |

- One test file per module, and one helper module:

| File | Tests |
|------|-------|
| `test_plane.py` | `plane.py` |
| `test_nrrd_reader.py` | `nrrd_reader.py` |
| `test_projector.py` | `projector.py` |
| `test_video_writer.py` | `video_writer.py` |
| `test_demo.py` | `Ex0.py`, run as a separate process |
| `test_pipeline.py` | `pipeline.py`: the messages and the frame callback shared by `Ex0.py` and the GUI |
| `test_preview.py` | `preview.py`: the GUI helpers, including the planes of the explore sliders |
| `test_user_data.py` | the whole program on real NRRD files (level 7) |
| `nrrd_files.py` | helper: writes small valid and broken NRRD files for the tests |
| `conftest.py` | pytest configuration: the options `--nrrd` and `--csv` |

## Test levels

### 1. Unit tests
Each module is tested on its own (NFR-4).

**NRRD reader** (`test_nrrd_reader.py`). Test files are generated inside the test (temporary folder), not stored in the repository.
- Reads every supported type: uint8, uint16, int16, uint32; raw and gzip encoding (8 combinations).
- Index order `M[x][y][z]`, negative values (signed 16 bit), minimal volume `1 x 1 x 1`, other type names.
- Errors, each with a clear message (FR-3): missing file, a text file that is not NRRD, not 3D, a size of `1024`, an unsupported type (float), truncated data, damaged gzip data.

**Plane** (`test_plane.py`)
- Valid triangles and trapezoids, including a rectangle (top edge = base) and decimal coordinates.
- Invalid planes [D9], each breaking exactly one rule: not isosceles, collinear points, `b = c`, identical points, unequal trapezoid legs, inverted trapezoid (`|a'a''| > |bc|`), trapezoid not on one plane.
- `TOLERANCE` boundary: a leg difference of `0.0005` is valid, `0.002` is invalid.
- CSV files: line numbers, error messages, comments and empty lines, spaces and Windows line endings, missing file, no planes.

**Projector** (`test_projector.py`), on small synthetic volumes with known values. Every test runs on both projectors.
- `round_half_up`: `2.5 -> 3`, `2.4 -> 2` [D2].
- `sample`: inside `M`, outside `M` -> 0, and a negative index -> 0 (Python would silently read from the end of the array) [D1], FR-8.
- Size of `E`: `floor(Dab) + 1` rows, `round(Dbc) + 1` columns [D3].
- The apex is sampled and is a single pixel in the centre of row 0 [D4, D5].
- Orientation: the `b` side is on the left, `a` on top [D7].

**Video writer** (`test_video_writer.py`)
- Normalisation [D8]: uint8 unchanged; percentiles for 16 bit; fallback for a volume more than 99.5% empty; a constant volume gives black.
- Frame size (largest frame, even numbers) and centring on black [D11].
- Error frames (Q&A 3b): black, with a red X and the text; long reasons are wrapped; they do not change the frame size.
- A real mp4 is written and read back: number of frames, order, size, 10 fps (FR-10), and the red X of an error frame.
- Errors: no frames, output folder missing.

### 2. Known-answer tests
Small volumes where the right answer is known in advance (`test_projector.py`):
- The example of [ALGORITHM.md](ALGORITHM.md) (`a = (3,0)`, `b = (0,4)`, `c = (6,4)`) gives exactly the triangle drawn there.
- A rectangle parallel to an axis gives exactly the corresponding slice of the volume.
- A plane completely outside `M` gives zeros; a plane partly outside gives zeros only outside (FR-8).
- In a volume with only the values 0, 80, 160, 255 (like the phantom of `data/make_phantom.py`), every projected pixel is one of these values: nearest neighbour does not create new values [D1].

### 3. Reference vs optimised implementation
The projector has two implementations:
- a **reference** implementation with plain loops, a direct translation of [ALGORITHM.md](ALGORITHM.md);
- an **optimised** implementation with numpy, for performance (NFR-1).

The reference is checked by the tests above. The optimised implementation must return **exactly the same image** as the reference for:
- 200 random valid planes (triangles and trapezoids, decimal coordinates, partly outside) on a random 16-bit volume;
- 30 random planes on MRHead (`slow`);
- 20 random planes on every file of the data tests (level 7).

### 4. Performance
NFR-1: average projection time of planes that cross the whole volume. Reading the file and encoding the video are not included.
- `slow`: 100 planes on `croissant.nrrd` (500^3); fails below 30 fps.
- `data`: 50 planes on every file of the data tests; prints the fps and fails below 30.
- Every run of `Ex0.py` prints the measured fps (FR-11).

### 5. Demo tests (`test_demo.py`)
`Ex0.py` is run as a separate process, exactly as the lecturer runs it: `python Ex0.py file.nrrd file.csv file.mp4`.
- Valid input: the mp4 file is created; the number of frames equals the number of planes in the CSV; the frame size is even (FR-10).
- Wrong number of arguments (0, 1, 2, 4): a usage message is printed, no traceback (FR-1).
- Missing NRRD or CSV file, CSV with no planes: a clear error message, no traceback, no mp4 file (FR-3, NFR-2).
- Invalid rows and planes: a warning with the line number for each, and an error frame in its place; the valid rows keep their places (FR-5).
- Timing summary: the output contains the reading time, the average time per plane with the fps, and the writing time (FR-11).
- Manual check: the videos of the experiment are watched to confirm they look as expected.

### 6. Portability
NFR-6: the fast tests run automatically on Windows, macOS and Linux with GitHub Actions on every push (`.github/workflows/tests.yml`).

### 7. Tests on your own files (`test_user_data.py`)
Anyone can run the whole program on their own volumes and planes:
```
pytest -m data                                       # every .nrrd file in data/
pytest -m data --nrrd my.nrrd --nrrd other.nrrd      # your own volumes
pytest -m data --nrrd my.nrrd --csv my.csv -s        # your own planes; -s shows the fps
```
For every NRRD file:
- it can be read (size, type and value range are printed);
- the optimised projector equals the reference on 20 random planes inside the volume;
- performance on 50 planes that cross the volume (fps printed, at least 30);
- `Ex0.py` writes a video with one frame per plane, with the given CSV file or with 20 planes generated for the size of the volume.

### 8. The optional GUI (`gui.py`)
The window itself is not tested automatically; everything it computes is in `pipeline.py` and `preview.py`, which are:
- `test_pipeline.py`: every message reaches the log, the frame callback is called once per frame in order, file errors are raised.
- `test_preview.py`: the preview keeps the proportions; every plane from the explore sliders is valid for every axis,
  tilt and top edge (triangles and trapezoids); a flat rectangle equals the slice of the volume pixel by pixel;
  a plane copied as a CSV line is read back unchanged.

Manual check (with `data/MRHead.nrrd`):

| Action | Expected |
|--------|----------|
| Run with `experiments/planes/MRHead.csv` | progress bar, frames shown while they are made, slider and Play afterwards, Open video plays the mp4 |
| Run with `tests/data/invalid_rows.csv` / `invalid_planes.csv` | warnings in the log with the line numbers; error frames with a red X in the preview and in the video |
| Run with `tests/data/no_planes.csv`, a missing file, a non-NRRD file or an output folder that does not exist | an error message box, no video |
| Explore: move position, tilt, axis and top edge | the projection follows the sliders; the Plane line has 9 values for a triangle and 12 for a trapezoid |
| Copy a plane, paste it into a CSV file, Run | the same image as in the explore view |

## Test data
| Data | Where | Used by |
|------|-------|---------|
| Small NRRD files (valid and broken) | generated inside the tests (`nrrd_files.py`) | unit and demo tests |
| CSV files (valid and invalid planes) | `tests/data/*.csv` (stored in the repository) | plane and demo tests |
| Course dataset (MRHead, croissant, ...) | `data/` (not in the repository, see [data/README.md](../data/README.md)) | `slow` and `data` tests, experiment |
| Your own files | anywhere, given with `--nrrd` and `--csv` | `data` tests |

CSV files in `tests/data/`:
- `valid_triangles.csv`, `valid_trapezoids.csv`: valid planes, including decimals and a `TOLERANCE` case
- `invalid_rows.csv`: wrong number of values, non-numeric and empty values, semicolons
- `invalid_planes.csv`: one broken rule per row (8 rows)
- `outside.csv`: planes completely and partly outside the volume
- `no_planes.csv`: only comments and empty lines

## Requirement coverage
| Requirement | Tests |
|-------------|-------|
| FR-1 | demo: wrong number of arguments |
| FR-2 | NRRD reader: types and encodings; data: every file can be read |
| FR-3 | NRRD reader: errors; plane: missing CSV, no planes; demo: missing files, no planes |
| FR-4 | plane: CSV parsing; demo: valid input |
| FR-5 | plane: invalid planes; video writer: error frames; demo: invalid rows and planes |
| FR-6 | projector unit and known-answer tests; reference vs optimised |
| FR-7 | plane and projector tests with trapezoids; random trapezoids in the comparison |
| FR-8 | projector: outside `M`, negative index |
| FR-9 | video writer: normalisation |
| FR-10 | video writer: real mp4; demo: number and size of frames |
| FR-11 | demo: timing summary is printed |
| NFR-1 | performance: `slow` on croissant, `data` on every file |
| NFR-2 | every error test checks that there is no traceback |
| NFR-3 | performance tests (the 500^3 volume is loaded once) |
| NFR-4 | each module has its own test file |
| NFR-5 | this table |
| NFR-6 | GitHub Actions on Windows, macOS and Linux |
| GUI (optional) | pipeline and preview tests; the manual check in level 8 |

## How to run
```
pytest                  # fast tests (no large files needed)
pytest -m slow -s       # performance and comparison on data/MRHead.nrrd and data/croissant.nrrd
pytest -m data -s       # every .nrrd file in data/, or your own files with --nrrd and --csv
```
