"""YouTube Data API v3 client (official). No Shorts endpoint — upload vertical <3min,
YouTube auto-classifies as a Short. Resumable upload via googleapiclient.
"""
from __future__ import annotations

from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload


def upload_short(credentials, video_path: str, title: str, description: str, privacy: str = "private") -> str:
    """Upload a vertical clip; YouTube classifies it as a Short automatically."""
    youtube = build("youtube", "v3", credentials=credentials)
    body = {"snippet": {"title": title, "description": description, "categoryId": "22"},
            "status": {"privacyStatus": privacy}}
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = req.execute()
    return response["id"]
