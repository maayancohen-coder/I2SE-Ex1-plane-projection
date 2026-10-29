"""Reading NRRD files into a 3D volume (numpy array + metadata)."""
import gzip
import zlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from projection.errors import VolumeError

MAX_SIZE = 2 ** 10      # every size must satisfy 1 <= size < 2^10 (assignment)

# NRRD type names -> numpy type (supported types, SRS section 2.1)
TYPES = {
    "uchar": "u1", "unsigned char": "u1", "uint8": "u1", "uint8_t": "u1",
    "ushort": "u2", "unsigned short": "u2", "unsigned short int": "u2", "uint16": "u2", "uint16_t": "u2",
    "short": "i2", "short int": "i2", "signed short": "i2", "signed short int": "i2", "int16": "i2", "int16_t": "i2",
    "uint": "u4", "unsigned int": "u4", "uint32": "u4", "uint32_t": "u4",
}


@dataclass(frozen=True)
class Volume:
    """A 3D volume M, indexed as data[x][y][z] (index coordinates, SRS decision 6)."""
    data: np.ndarray

    @property
    def shape(self) -> tuple:
        return self.data.shape

    @property
    def dtype(self) -> np.dtype:
        return self.data.dtype


def _parse_header(lines: list, path: Path) -> dict:
    if not lines or not lines[0].startswith("NRRD000"):
        raise VolumeError(f"{path} is not an NRRD file")
    fields = {}
    for line in lines[1:]:
        if line.startswith("#") or ":=" in line:      # comments and key/value pairs are ignored
            continue
        if ":" not in line:
            raise VolumeError(f"invalid header line in {path}: {line!r}")
        key, value = line.split(":", 1)
        fields[key.strip().lower()] = value.strip()
    return fields


def _split_header(raw: bytes, path: Path):
    """Return the header lines and the data bytes. The header ends with an empty line."""
    for separator in (b"\r\n\r\n", b"\n\n"):
        end = raw.find(separator)
        if end != -1:
            break
    else:
        raise VolumeError(f"{path} is not an NRRD file (no end of header)")
    try:
        header = raw[:end].decode("ascii")
    except UnicodeDecodeError:
        raise VolumeError(f"{path} is not an NRRD file") from None
    return header.splitlines(), raw[end + len(separator):]


def read_nrrd(path) -> Volume:
    """Read a 3D NRRD file (raw or gzip encoding) into a Volume (FR-2).

    Raises VolumeError for every problem with the file (FR-3).
    """
    path = Path(path)
    try:
        raw = path.read_bytes()
    except OSError as e:
        raise VolumeError(f"cannot read the NRRD file {path}: {e.strerror or e}") from None

    lines, data = _split_header(raw, path)
    fields = _parse_header(lines, path)

    if "data file" in fields or "datafile" in fields:
        raise VolumeError(f"{path}: detached data files are not supported")

    type_name = fields.get("type", "").lower()
    if type_name not in TYPES:
        raise VolumeError(f"{path}: unsupported type {fields.get('type')!r} "
                          "(supported: unsigned 8, 16, 32 bit and signed 16 bit)")

    if fields.get("dimension") != "3":
        raise VolumeError(f"{path}: the volume must be 3D, got dimension {fields.get('dimension')!r}")

    try:
        sizes = [int(s) for s in fields.get("sizes", "").split()]
    except ValueError:
        raise VolumeError(f"{path}: invalid sizes {fields.get('sizes')!r}") from None
    if len(sizes) != 3 or not all(1 <= s < MAX_SIZE for s in sizes):
        raise VolumeError(f"{path}: every size must be between 1 and {MAX_SIZE - 1}, got {sizes}")

    encoding = fields.get("encoding", "").lower()
    if encoding in ("gzip", "gz"):
        try:
            data = gzip.decompress(data)
        except (OSError, EOFError, zlib.error) as e:
            raise VolumeError(f"{path}: the compressed data is damaged ({e})") from None
    elif encoding != "raw":
        raise VolumeError(f"{path}: unsupported encoding {fields.get('encoding')!r} (supported: raw, gzip)")

    dtype = np.dtype(TYPES[type_name])
    if dtype.itemsize > 1:
        endian = fields.get("endian", "little").lower()
        dtype = dtype.newbyteorder("<" if endian == "little" else ">")

    sx, sy, sz = sizes
    expected = sx * sy * sz * dtype.itemsize
    if len(data) < expected:
        raise VolumeError(f"{path}: the data is truncated ({len(data)} of {expected} bytes)")

    # NRRD stores x as the fastest axis: in numpy order the array is [z][y][x].
    # The transposed view gives data[x][y][z] without copying the data.
    zyx = np.frombuffer(data, dtype=dtype, count=sx * sy * sz).reshape(sz, sy, sx)
    return Volume(zyx.astype(dtype.newbyteorder("="), copy=False).transpose(2, 1, 0))