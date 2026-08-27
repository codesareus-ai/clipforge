"""RenderService: cut clip with ffmpeg, then render branded 9:16 with Remotion."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.config import get_settings

settings = get_settings()


def cut(source: str, start: float, end: float, out_path: str) -> str:
    """Cut [start,end] from source using ffmpeg (re-encode for frame accuracy)."""
    cmd = [
        settings.FFMPEG_BIN, "-y", "-i", source,
        "-ss", str(start), "-to", str(end),
        "-c:v", "libx264", "-c:a", "aac", "-preset", "fast", out_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_path


def render_captioned(clip_path: str, captions: list[dict], reframe: list[dict], meta: dict, out_path: str) -> str:
    """Render final 9:16 clip with captions/branding + face-track reframe via Remotion.

    `captions` = [{text,start,end}] in seconds; `reframe` = [{t,x,y,scale}] keyframes
    (see services/reframe.py); `meta` = {title, branding}.
    Data is passed to the Remotion composition through a JSON prop file, then `npx remotion render`.
    Requires `npm install` in the Remotion project (frontend/) for the render to run.
    """
    props = {"clip": clip_path, "captions": captions, "reframe": reframe, "meta": meta}
    prop_file = Path(settings.OUTPUT_DIR) / "props.json"
    prop_file.write_text(json.dumps(props))
    cmd = [
        "npx", "remotion", "render", "CaptionedClip",
        "--props", str(prop_file),
        "--output", out_path,
    ]
    subprocess.run(cmd, cwd=settings.REMOTION_PROJECT_DIR, check=True, capture_output=True)
    return out_path
