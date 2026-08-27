"""IngestService: download long-form video from YouTube/Twitch via yt-dlp + streamlink."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from app.config import get_settings

settings = get_settings()


class IngestError(RuntimeError):
    pass


def _run(cmd: list[str]) -> str:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise IngestError(proc.stderr or proc.stdout)
    return proc.stdout


def download(url: str, out_dir: str, *, live: bool = False, height: str = "max") -> str:
    """Return local path to downloaded video. `live=True` uses streamlink for HLS/DASH."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if live:
        cmd = [
            "streamlink", url, "best",
            "-o", str(out_dir / "%(title)s.%(ext)s"),
        ]
    else:
        cmd = [
            "yt-dlp", url,
            "-f", f"bv*[height<={height}]+ba/best",
            "-o", str(out_dir / "%(id)s.%(ext)s"),
        ]
    _run(cmd)
    files = sorted(out_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        raise IngestError("download produced no file")
    return str(files[0])


def get_metadata(url: str) -> dict:
    out = _run(["yt-dlp", "--dump-json", "--no-download", url])
    return json.loads(out)
