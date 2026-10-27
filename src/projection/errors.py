"""Errors of the program. Ex0.py catches ProjectionError and prints a clear message (NFR-2)."""


class ProjectionError(Exception):
    """Base class for every expected error that stops the run."""


class VolumeError(ProjectionError):
    """The NRRD file is missing, unreadable or not supported (FR-3)."""


class PlaneFileError(ProjectionError):
    """The CSV file is missing, unreadable or contains no planes (FR-3)."""


class OutputError(ProjectionError):
    """The output video cannot be written."""


class PlaneError(ValueError):
    """A single plane is invalid. Not fatal: only its own frame is affected (SRS decision 9)."""