import numpy as np
import pytest

from projection.errors import OutputError
from projection.nrrd_reader import Volume
from projection.video_writer import ERROR_FRAME_SIZE, ErrorFrame, Normalizer, VideoWriter, frame_size, pad


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


# ---------- error frames (SRS decision 9, assignment Q&A 3b) ----------

def test_error_frame_is_black_with_a_red_x_and_text():
    frame = ErrorFrame("planes.csv line 12", "not a number: 'abc'").render((200, 300))
    assert frame.shape == (200, 300, 3)
    red = (frame[:, :, 0] > 150) & (frame[:, :, 1] < 100)
    white = frame.min(axis=2) > 200
    assert red.any()                                        # the X
    assert white.any()                                      # the text
    assert frame[100, 5].tolist() == [0, 0, 0]              # the background is black


def test_long_reason_is_wrapped_into_the_frame():
    reason = "top edge longer than the base: |a'a''| = 160.0000, |bc| = 60.0000"
    frame = ErrorFrame("planes.csv line 16", reason).render((120, 160))
    assert frame.shape == (120, 160, 3)


def test_error_frames_do_not_change_the_frame_size():
    frames = [np.zeros((30, 40), dtype=np.uint8), ErrorFrame("f.csv line 1", "bad")]
    assert frame_size(frames) == (30, 40)


def test_only_error_frames_use_a_default_size():
    assert frame_size([ErrorFrame("f.csv line 1", "bad")]) == ERROR_FRAME_SIZE


def test_video_with_an_error_frame(tmp_path):
    imageio = pytest.importorskip("imageio.v2")
    frames = [np.full((120, 160), 120, dtype=np.uint8), ErrorFrame("f.csv line 3", "not a number: 'x'")]
    path = tmp_path / "out.mp4"
    VideoWriter().write(path, frames)
    with imageio.get_reader(path) as reader:
        read = [frame for frame in reader]
    assert len(read) == 2
    assert (read[1][:, :, 0].astype(int) - read[1][:, :, 1]).max() > 60     # the second frame has red in it
