"""RenderService: real ffmpeg cut + 9:16 reframe + caption burn.

The Remotion path is the premium render (web font captions, branding, motion),
but it requires `npm install` in the frontend and a heavier toolchain. This
module provides a *real* ffmpeg-based pipeline that works with no JS deps:
  1. cut([start,end])            -> re-encoded slice (frame-accurate enough)
  2. render_captioned(...)       -> 9:16 reframe (face-track pan from keyframes)
                                    + caption burn + branding overlay

The 9:16 reframe uses the keyframes produced by services/reframe.py:
each keyframe is {t, x, y, scale} where (x,y) is the crop-center in the
source's normalized [0..1] coordinate space and scale is zoom (1.0 = fit).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from app.config import get_settings

settings = get_settings()

# Vertical short-form target.
TARGET_W, TARGET_H = 1080, 1920
BRAND = "ClipForge"


def _run(cmd: list[str]) -> None:
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed ({res.returncode}): {res.stderr[-600:]}"
        )


def cut(source: str, start: float, end: float, out_path: str) -> str:
    """Cut [start,end] from source using ffmpeg (re-encode for frame accuracy)."""
    cmd = [
        settings.FFMPEG_BIN, "-y", "-ss", f"{start:.3f}", "-to", f"{end:.3f}",
        "-i", source,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        out_path,
    ]
    _run(cmd)
    return out_path


def _reframe_filter(keyframes: list[dict], src_w: int, src_h: int) -> str:
    """Build an ffmpeg video filter that crops to 9:16 using the keyframes.

    Keyframes are sparse; we use the median keyframe's (x,y) center + scale to
    derive a single centered crop window, then scale to 1080x1920. Robust on
    every ffmpeg build (no zoompan multi-key interpolation fragility).
    """
    if not keyframes:
        # Simple contain-and-pad (letterbox) to 9:16, centered.
        return (
            f"scale={TARGET_W}:{TARGET_H}:force_original_aspect_ratio=decrease,"
            f"pad={TARGET_W}:{TARGET_H}:(ow-iw)/2:(oh-ih)/2,setsar=1"
        )

    kf = keyframes[len(keyframes) // 2]
    x = max(0.0, min(1.0, kf.get("x", 0.5)))
    y = max(0.0, min(1.0, kf.get("y", 0.5)))
    scale = max(1.0, min(2.5, float(kf.get("scale", 1.0))))
    # 9:16 region at this zoom.
    cw = min(src_w, int(src_h * TARGET_W / TARGET_H / scale))
    ch = int(cw * TARGET_H / TARGET_W)
    cx = int(max(0, min(src_w - cw, x * src_w - cw / 2)))
    cy = int(max(0, min(src_h - ch, y * src_h - ch / 2)))
    return (
        f"crop={cw}:{ch}:{cx}:{cy},"
        f"scale={TARGET_W}:{TARGET_H}:flags=lanczos,setsar=1"
    )


def render_captioned(
    clip_path: str, captions: list[dict], reframe: list[dict], meta: dict, out_path: str
) -> str:
    """Render a real 9:16 clip: reframe + caption burn + branding overlay.

    Uses ffmpeg only (no Remotion). Produces a vertical mp4 at 1080x1920 with
    burned-in captions and a bottom branding bug.

    Captions are burned with `drawtext` (one filter per line, timed with
    enable='between(t,start,end)') — this avoids the fragile subtitles-filter
    style parser and works on any ffmpeg build.
    """
    import re

    Path(settings.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    # Probe source dimensions for the reframe crop math.
    probe = subprocess.run(
        [settings.FFMPEG_BIN, "-y", "-i", clip_path],
        capture_output=True, text=True,
    )
    src_w = src_h = 1280  # sensible default if probe fails
    for line in probe.stderr.splitlines():
        if "Stream #0" in line and "Video:" in line:
            m = re.search(r"(\d{2,5})x(\d{2,5})", line)
            if m:
                src_w, src_h = int(m.group(1)), int(m.group(2))
            break

    vfilter = _reframe_filter(reframe, src_w, src_h)

    # Caption burn: one drawtext per line, timed, centered, large + outlined.
    cap_filters = []
    for c in captions:
        text = c["text"].replace("\\", r"\\").replace("'", r"\'").replace(":", r"\:")
        cap_filters.append(
            f"drawtext=text='{text}':fontcolor=white:fontsize=64:"
            f"x=(w-tw)/2:y=h-th-260:"
            f"box=1:boxcolor=black@0.45:boxborderw=16:"
            f"enable='between(t,{c['start']:.2f},{c['end']:.2f})'"
        )
    caps = ",".join(cap_filters) if cap_filters else "null"

    # Branding bug bottom-center.
    brand = (
        f"drawtext=text='{meta.get('branding', BRAND)}':"
        f"fontcolor=white:fontsize=40:alpha=0.85:"
        f"x=(w-tw)/2:y=h-th-60:box=1:boxcolor=black@0.4:boxborderw=12"
    )
    full_vfilter = f"{vfilter},{caps},{brand}"

    cmd = [
        settings.FFMPEG_BIN, "-y", "-i", clip_path,
        "-vf", full_vfilter,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k",
        "-movflags", "+faststart",
        out_path,
    ]
    _run(cmd)
    return out_path
