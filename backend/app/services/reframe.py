"""ReframeService: smooth face-track 9:16 crop keyframes for Remotion.

Samples the clip, detects the primary face per frame with MediaPipe, then
smooths the crop center with a DEADZONE + exponential moving average so the
9:16 crop pans gently toward the speaker and ignores tiny jittery movements.
Falls back to a static center crop if MediaPipe isn't available.

Output: list of {t, x, y, scale} keyframes (t in seconds) the renderer interpolates.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

TARGET_W, TARGET_H = 1080, 1920  # 9:16
DEADZONE = 0.04    # fraction of frame; movements smaller than this are ignored
ALPHA = 0.35       # EMA smoothing factor
MIN_SCALE = 1.0


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def compute_reframe(video_path: str, fps_sample: float = 2.0) -> list[dict]:
    from app.config import get_settings

    ffmpeg = get_settings().FFMPEG_BIN
    frames = _extract_frames(video_path, fps_sample, ffmpeg)
    if not frames:
        return [{"t": 0.0, "x": 0.5, "y": 0.5, "scale": 1.0}]
    pairs = []
    for f in frames:
        c = _face_center(f)
        if c:
            pairs.append((f, c))
    if not pairs:
        return [{"t": 0.0, "x": 0.5, "y": 0.5, "scale": 1.0}]
    centers = _deadzone_ema([c for _, c in pairs])
    out = []
    for (f, _), c in zip(pairs, centers):
        scale = max(MIN_SCALE, (f["w"] / f["h"]) / (TARGET_W / TARGET_H)) if f["h"] else 1.0
        out.append({"t": float(f["t"]), "x": c["x"], "y": c["y"], "scale": scale})
    return out


def _extract_frames(video_path, fps, ffmpeg):
    d = Path(tempfile.mkdtemp())
    subprocess.run([ffmpeg, "-y", "-i", video_path, "-vf", f"fps={fps}", str(d / "f_%04d.jpg")],
                   capture_output=True)
    files = sorted(p for p in os.listdir(d) if p.endswith(".jpg"))
    return [{"path": str(d / p), "t": i / fps, "w": 0, "h": 0} for i, p in enumerate(files)]


def _face_center(frame):
    try:
        import numpy as np
        from PIL import Image
        import mediapipe as mp
    except Exception:  # noqa: BLE001
        return None
    with Image.open(frame["path"]) as img:
        arr = np.array(img.convert("RGB"))
    frame["h"], frame["w"] = arr.shape[:2]
    det = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)
    res = det.process(arr)
    if not res.detections:
        return None
    det0 = max(res.detections, key=lambda d: d.location_data.relative_bounding_box.width)
    bb = det0.location_data.relative_bounding_box
    return {"x": bb.xmin + bb.width / 2, "y": bb.ymin + bb.height / 2}


def _deadzone_ema(centers):
    """EMA smoothing that HOLDS position for sub-deadzone movements (anti-jitter)."""
    out = []
    cur = {"x": centers[0]["x"], "y": centers[0]["y"]}
    for c in centers:
        for axis in ("x", "y"):
            delta = c[axis] - cur[axis]
            if abs(delta) >= DEADZONE:
                cur[axis] = cur[axis] * (1 - ALPHA) + c[axis] * ALPHA
            # else: deadzone -> hold position (no update)
        out.append({"x": _clamp(cur["x"]), "y": _clamp(cur["y"])})
    return out
