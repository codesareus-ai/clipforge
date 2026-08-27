"""Keyframe extraction tests (real ffmpeg via imageio-ffmpeg; skips if absent)."""
import shutil
import subprocess

import pytest

from app.config import get_settings
from app.services import keyframes


@pytest.fixture(scope="module")
def ffmpeg_bin():
    settings = get_settings()
    bin = settings.FFMPEG_BIN
    if shutil.which(bin) or (isinstance(bin, str) and shutil.os.path.exists(bin)):
        return bin
    pytest.skip("no ffmpeg binary available")


def _make_clip(bin, path):
    subprocess.run(
        [bin, "-y", "-f", "lavfi",
         "-i", "testsrc=size=1280x720:rate=30:duration=6",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=6",
         "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-c:a", "aac", str(path)],
        check=True, capture_output=True,
    )


def test_uniform_keyframes(ffmpeg_bin, tmp_path):
    clip = tmp_path / "c.mp4"
    _make_clip(ffmpeg_bin, clip)
    out = tmp_path / "kf"
    frames = keyframes.extract_keyframes(str(clip), str(out), mode="uniform", count=3)
    assert len(frames) == 3
    assert all(f.endswith(".jpg") for f in frames)


def test_scene_keyframes(ffmpeg_bin, tmp_path):
    clip = tmp_path / "c.mp4"
    _make_clip(ffmpeg_bin, clip)
    out = tmp_path / "kfs"
    frames = keyframes.extract_keyframes(str(clip), str(out), mode="scene")
    # testsrc has little motion, but the call must succeed and return a list
    assert isinstance(frames, list)
    if frames:
        assert all(f.endswith(".jpg") for f in frames)
