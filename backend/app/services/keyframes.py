"""Keyframe extraction service (ffmpeg-based, no ML dependency).

Produces still frames used by:
  - the vision-LLM moment scorer (rank_moments_vision)
  - smarter reframe (scene-aware crop centers)

Two modes:
  - "uniform": N evenly-spaced frames across [start,end]
  - "scene":   ffmpeg scene-change detection (select=gt(scene,N)) -> keyframes
Both write .jpg files and return their paths (sorted by timestamp).
"""
from __future__ import annotations

import subprocess
import re
from pathlib import Path

from app.config import get_settings

settings = get_settings()


def extract_keyframes(
    source: str,
    out_dir: str,
    mode: str = "uniform",
    count: int = 3,
    start: float | None = None,
    end: float | None = None,
) -> list[str]:
    """Extract keyframe .jpg files from `source`. Returns sorted file paths.

    `mode="uniform"`: `count` evenly spaced frames (optionally within
        [start,end]).
    `mode="scene"`:   ffmpeg scene-change filter (threshold 0.3) across the
        whole clip; `count` is ignored (scene detection drives it).
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    seek = ""
    if start is not None:
        seek = f"-ss {start:.3f}"
        if end is not None:
            seek += f" -to {end:.3f}"

    if mode == "scene":
        # Scene-change detection: keep frames where scene diff > 0.3.
        filter_expr = "select=gt(scene\\,0.3)"
        cmd = [
            settings.FFMPEG_BIN, "-y", *seek.split(), "-i", source,
            "-vf", f"{filter_expr},showinfo", "-vsync", "vfr",
            "-frames:v", "40",
            f"{out_dir}/scene_%03d.jpg",
        ]
    else:
        # Uniform: one frame every (duration/count). Use fps filter.
        fps = max(0.1, 1.0 / max(0.1, _clip_duration(source, start, end) / count)) \
            if (start is not None or end is not None) else (count / max(0.1, _duration(source)))
        cmd = [
            settings.FFMPEG_BIN, "-y", *seek.split(), "-i", source,
            "-vf", f"fps={fps:.4f}",
            "-frames:v", str(count),
            f"{out_dir}/frame_%03d.jpg",
        ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"keyframe extract failed ({res.returncode}): {res.stderr[-400:]}")

    files = sorted(
        str(p) for p in Path(out_dir).glob("*.jpg")
        if re.match(r"(frame|scene)_\d+\.jpg", p.name)
    )
    return files


def _duration(source: str) -> float:
    return _probe_duration(source)


def _clip_duration(source: str, start: float | None, end: float | None) -> float:
    d = _probe_duration(source)
    if start is not None and end is not None:
        return max(0.1, end - start)
    return d


def _probe_duration(source: str) -> float:
    res = subprocess.run(
        [settings.FFMPEG_BIN, "-i", source],
        capture_output=True, text=True,
    )
    m = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", res.stderr)
    if not m:
        return 10.0
    h, mi, s = int(m.group(1)), int(m.group(2)), float(m.group(3))
    return h * 3600 + mi * 60 + s
