import gzip

import numpy as np
import pytest

from nrrd_files import numbered_volume, write_nrrd
from projection.errors import VolumeError
from projection.nrrd_reader import read_nrrd


# ---------- valid files (FR-2) ----------

@pytest.mark.parametrize("dtype", [np.uint8, np.uint16, np.int16, np.uint32])
@pytest.mark.parametrize("encoding", ["raw", "gzip"])
def test_reads_every_supported_type_and_encoding(tmp_path, dtype, encoding):
    expected = numbered_volume(dtype=dtype)
    volume = read_nrrd(write_nrrd(tmp_path / "v.nrrd", expected, encoding=encoding))
    assert volume.shape == (4, 5, 6)
    assert volume.dtype == dtype
    assert np.array_equal(volume.data, expected)


def test_index_order_is_x_y_z(tmp_path):
    volume = read_nrrd(write_nrrd(tmp_path / "v.nrrd", numbered_volume()))
    assert volume.data[3, 0, 0] == 3        # v = x + 10*y + 100*z
    assert volume.data[0, 4, 0] == 40
    assert volume.data[0, 0, 5] == 500


def test_signed_16_bit_keeps_negative_values(tmp_path):
    m = np.full((2, 2, 2), -7, dtype=np.int16)
    assert read_nrrd(write_nrrd(tmp_path / "v.nrrd", m)).data.min() == -7


def test_minimal_volume(tmp_path):
    m = np.array([[[42]]], dtype=np.uint8)
    assert read_nrrd(write_nrrd(tmp_path / "v.nrrd", m)).data[0, 0, 0] == 42


def test_type_names_from_other_tools(tmp_path):
    m = numbered_volume(dtype=np.uint8)
    assert read_nrrd(write_nrrd(tmp_path / "v.nrrd", m, nrrd_type="unsigned char")).dtype == np.uint8


# ---------- errors (FR-3) ----------

def test_missing_file(tmp_path):
    with pytest.raises(VolumeError, match="cannot read"):
        read_nrrd(tmp_path / "missing.nrrd")


def test_text_file_is_not_nrrd(tmp_path):
    f = tmp_path / "text.nrrd"
    f.write_text("hello\n\nworld")
    with pytest.raises(VolumeError, match="not an NRRD file"):
        read_nrrd(f)


def test_not_3d(tmp_path):
    header = "NRRD0004\ntype: uint8\ndimension: 2\nsizes: 4 4\nencoding: raw\n"
    with pytest.raises(VolumeError, match="must be 3D"):
        read_nrrd(write_nrrd(tmp_path / "v.nrrd", None, header=header, data=bytes(16)))


def test_size_out_of_range(tmp_path):
    header = "NRRD0004\ntype: uint8\ndimension: 3\nsizes: 1024 1 1\nencoding: raw\n"
    with pytest.raises(VolumeError, match="between 1 and 1023"):
        read_nrrd(write_nrrd(tmp_path / "v.nrrd", None, header=header, data=bytes(1024)))


def test_unsupported_type(tmp_path):
    m = np.zeros((2, 2, 2), dtype=np.float32)
    with pytest.raises(VolumeError, match="unsupported type"):
        read_nrrd(write_nrrd(tmp_path / "v.nrrd", m, nrrd_type="float", data=m.tobytes()))


def test_truncated_data(tmp_path):
    m = numbered_volume(dtype=np.uint16)
    data = m.transpose(2, 1, 0).tobytes()[:-10]
    with pytest.raises(VolumeError, match="truncated"):
        read_nrrd(write_nrrd(tmp_path / "v.nrrd", m, encoding="raw", data=data))


def test_damaged_gzip_data(tmp_path):
    m = numbered_volume(dtype=np.uint8)
    data = gzip.compress(m.tobytes())[:20]
    with pytest.raises(VolumeError, match="damaged"):
        read_nrrd(write_nrrd(tmp_path / "v.nrrd", m, data=data))
