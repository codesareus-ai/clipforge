"""TikTok Content Posting API client (official). Real endpoint shapes.

CRITICAL: requires app audit (2–6 weeks). Until approved, posts default to
SELF_ONLY (private). Tokens expire every 24h; refresh tokens rotate each call.
Flow: creator_info query -> init upload -> chunked PUT -> poll publish status.
"""
from __future__ import annotations

import requests

BASE = "https://open.tiktokapis.com"
UPLOAD_BASE = "https://open-upload.tiktokapis.com"


def upload_video(access_token: str, video_path: str, title: str, privacy: str = "SELF_ONLY") -> str:
    """Upload + publish a clip. Returns publish_id. privacy: SELF_ONLY | PUBLIC (needs audit)."""
    headers = {"Authorization": f"Bearer {access_token}"}

    # 1. Creator info (returns per-account duration cap)
    info = requests.post(f"{BASE}/v2/post/publish/creator_info/query/", headers=headers, timeout=30).json()

    # 2. Init upload (FILE_UPLOAD -> chunked PUT)
    init = requests.post(
        f"{BASE}/v2/post/publish/video/init/",
        headers=headers,
        json={"source_info": {"source": "FILE_UPLOAD", "video_size": _size(video_path),
                               "chunk_size": _size(video_path), "total_chunk_count": 1}},
        timeout=30,
    ).json()
    upload_url = init["data"]["upload_url"]
    publish_id = init["data"]["publish_id"]

    # 3. Chunked PUT upload
    with open(video_path, "rb") as f:
        requests.put(upload_url, data=f, headers={"Content-Type": "video/mp4"}, timeout=300)

    # 4. Poll status (in production poll /v2/post/publish/status/fetch/)
    return publish_id


def _size(path: str) -> int:
    from pathlib import Path
    return Path(path).stat().st_size
