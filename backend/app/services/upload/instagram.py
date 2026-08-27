"""Instagram Graph API client (official). Reels via container model + resumable upload.

CRITICAL: Reels via API capped at 90s. Video must be at a PUBLIC URL (Meta pulls)
or use resumable upload. Requires Business/Creator account + instagram_content_publish.
"""
from __future__ import annotations

import requests

GRAPH = "https://graph.facebook.com"


def create_reel_container(ig_user_id: str, access_token: str, video_url: str, caption: str) -> str:
    r = requests.post(
        f"{GRAPH}/{ig_user_id}/media",
        data={"media_type": "REELS", "video_url": video_url, "caption": caption,
              "access_token": access_token},
        timeout=30,
    ).json()
    return r["id"]


def publish_reel(ig_user_id: str, access_token: str, container_id: str) -> str:
    r = requests.post(
        f"{GRAPH}/{ig_user_id}/media_publish",
        data={"creation_id": container_id, "access_token": access_token},
        timeout=30,
    ).json()
    return r["id"]


def upload_reel(ig_user_id: str, access_token: str, public_video_url: str, caption: str) -> str:
    """Public-URL flow. For local files, host on S3/R2 first (see OutputStorage)."""
    cid = create_reel_container(ig_user_id, access_token, public_video_url, caption)
    return publish_reel(ig_user_id, access_token, cid)
