"""Render tests: real ffmpeg cut + reframe when a binary is available.

These tests are skipped automatically on CI runners / machines without an
ffmpeg binary (the app auto-detects imageio-ffmpeg, but we don't install it
in the test deps to keep CI light). Run locally to exercise the real media
path:  uv pip install imageio-ffmpeg && pytest tests/test_render.py -q
"""
import shutil

import pytest

from app.config import get_settings
from app.services import render


@pytest.fixture(scope="module")
def ffmpeg_bin():
    settings = get_settings()
    bin = settings.FFMPEG_BIN
    if shutil.which(bin) or (isinstance(bin, str) and shutil.os.path.exists(bin)):
        return bin
    pytest.skip("no ffmpeg binary available")


def test_reframe_no_keyframes_is_916(ffmpeg_bin):
    f = render._reframe_filter([], 1280, 720)
    assert "pad=1080:1920" in f  # letterbox to 9:16


def test_reframe_with_keyframe_crops_and_scales(ffmpeg_bin):
    f = render._reframe_filter([{"t": 0, "x": 0.5, "y": 0.5, "scale": 1.0}],
                               1280, 720)
    assert "crop=" in f
    assert "scale=1080:1920" in f


def test_cut_produces_playable_clip(ffmpeg_bin, tmp_path):
    settings = get_settings()
    sample = tmp_path / "sample.mp4"
    # Generate a tiny test clip.
    import subprocess

    subprocess.run(
        [ffmpeg_bin, "-y", "-f", "lavfi",
         "-i", "testsrc=size=1280x720:rate=30:duration=3",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
         "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-c:a", "aac", str(sample)],
        check=True, capture_output=True,
    )
    out = tmp_path / "cut.mp4"
    render.cut(str(sample), 0.5, 2.0, str(out))
    assert out.exists() and out.stat().st_size > 0


def test_render_captioned_vertical(ffmpeg_bin, tmp_path):
    settings = get_settings()
    sample = tmp_path / "sample.mp4"
    import subprocess

    subprocess.run(
        [ffmpeg_bin, "-y", "-f", "lavfi",
         "-i", "testsrc=size=1280x720:rate=30:duration=4",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
         "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-c:a", "aac", str(sample)],
        check=True, capture_output=True,
    )
    cut = tmp_path / "cut.mp4"
    render.cut(str(sample), 0.5, 3.0, str(cut))
    final = tmp_path / "final.mp4"
    render.render_captioned(
        str(cut),
        [{"text": "the part everyone quotes", "start": 0.0, "end": 2.5}],
        [{"t": 0, "x": 0.5, "y": 0.5, "scale": 1.0}],
        {"title": "hook", "branding": "@demo"},
        str(final),
    )
    # Confirm vertical 9:16 via ffmpeg probe on stderr.
    res = subprocess.run([ffmpeg_bin, "-i", str(final)],
                         capture_output=True, text=True)
    assert "1080x1920" in res.stderr
