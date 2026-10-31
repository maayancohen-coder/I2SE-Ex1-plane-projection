"""pytest configuration: lets the tests run on any NRRD and CSV file given on the command line.

    pytest -m data                                   # every .nrrd file in data/
    pytest -m data --nrrd my.nrrd --nrrd other.nrrd  # your own volumes
    pytest -m data --nrrd my.nrrd --csv my.csv -s    # your own planes; -s shows the measured fps
"""
from pathlib import Path

import pytest

DATASET = Path(__file__).parent.parent / "data"


def pytest_addoption(parser):
    parser.addoption("--nrrd", action="append", default=[],
                     help="NRRD file for the data tests (can be repeated); default: every .nrrd file in data/")
    parser.addoption("--csv", default=None,
                     help="CSV file of planes for the demo data test; default: planes generated for each volume")


def pytest_generate_tests(metafunc):
    """Run every test that has an nrrd_path argument once for each NRRD file."""
    if "nrrd_path" in metafunc.fixturenames:
        given = metafunc.config.getoption("--nrrd")
        paths = [Path(p) for p in given] if given else sorted(DATASET.glob("*.nrrd"))
        metafunc.parametrize("nrrd_path", paths, ids=[p.name for p in paths])


@pytest.fixture
def csv_path(request):
    """The CSV file given with --csv, or None."""
    value = request.config.getoption("--csv")
    return Path(value) if value else None
