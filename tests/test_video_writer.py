import numpy as np
import pytest

from projection.errors import OutputError
from projection.nrrd_reader import Volume
from projection.video_writer import Normalizer, VideoWriter, frame_size, pad


# ---------- Normalizer [D8] ----------

def test_uint8_is_unchanged():
    image = np.array([[0, 7, 255]], dtype=np.uint8)
    normalizer = Normalizer(Volume(np.zeros((2, 2, 2), dtype=np.uint8)))
    assert np.array_equal(normalizer.to_uint8(image), image)


def test_16_bit_uses_percentiles():
    data = np.arange(1000, dtype=np.uint16).reshape(10, 10, 10)
    data[0, 0, 0] = 60000                                   # one extreme voxel must not darken everything
    normalizer = Normalizer(Volume(data))
    lo, hi = normalizer.range
    assert hi < 1000
    out = normalizer.to_uint8(np.array([[lo, hi, 60000]], dtype=np.float64))
    assert list(out[0]) == [0, 255, 255]                    # clipped above hi


def test_fallback_keeps_a_small_object():
    data = np.zeros((20, 20, 20), dtype=np.uint16)          # more than 99.5% empty
    data[10, 10, 10] = 500
    normalizer = Normalizer(Volume(data))
    assert normalizer.range == (0, 500)                     # min/max instead of equal percentiles
    assert normalizer.to_uint8(np.array([[500]], dtype=np.uint16))[0, 0] == 255


def test_constant_volume_gives_black():
    normalizer = Normalizer(Volume(np.full((5, 5, 5), 300, dtype=np.uint16)))
    assert not normalizer.to_uint8(np.full((3, 3), 300, dtype=np.uint16)).any()


# ---------- frame size and padding [D11] ----------

def test_frame_size_is_the_largest_and_even():
    frames = [np.zeros((7, 4)), np.zeros((3, 11))]
    assert frame_size(frames) == (8, 12)


def test_pad_centres_the_frame_on_black():
    out = pad(np.full((2, 2), 9, dtype=np.uint8), (4, 6))
    assert out.shape == (4, 6)
    assert out[1:3, 2:4].tolist() == [[9, 9], [9, 9]]
    assert out.sum() == 4 * 9


# ---------- writing the video (FR-10) ----------

def test_writes_all_frames_in_one_size(tmp_path):
    imageio = pytest.importorskip("imageio.v2")
    frames = [np.full((30, 40), 50 * i, dtype=np.uint8) for i in range(5)] + [np.zeros((11, 13), dtype=np.uint8)]
    path = tmp_path / "out.mp4"
    assert VideoWriter().write(path, frames) == (30, 40)
    with imageio.get_reader(path) as reader:
        assert reader.get_meta_data()["fps"] == 10
        read = [frame for frame in reader]
    assert len(read) == 6
    assert read[0].shape[:2] == (30, 40)
    assert abs(int(read[4].mean()) - 200) <= 3              # the frames stay in their order


def test_no_frames_is_an_error(tmp_path):
    with pytest.raises(OutputError):
        VideoWriter().write(tmp_path / "out.mp4", [])


def test_output_folder_missing_is_an_error(tmp_path):
    with pytest.raises(OutputError, match="cannot write"):
        VideoWriter().write(tmp_path / "missing" / "out.mp4", [np.zeros((4, 4), dtype=np.uint8)])
