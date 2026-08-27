"""Dispatch a rendered clip to each requested platform using stored tokens."""
from __future__ import annotations

import json

from app.config import get_settings
from app.services.upload import vault
from app.services.upload import tiktok, instagram, youtube as yt_client, storage

settings = get_settings()


def publish_clip(user_id: str, platform: str, clip_path: str, public_url: str,
                 title: str, caption: str) -> dict:
    raw = vault.load_token(user_id, platform)
    if not raw:
        return {"platform": platform, "ok": False, "error": "no token — re-auth required"}
    blob = json.loads(raw)
    try:
        if platform == "tiktok":
            # privacy SELF_ONLY until app passes TikTok Content Posting audit
            pid = tiktok.upload_video(blob["access_token"], clip_path, title,
                                      privacy="SELF_ONLY")
            return {"platform": platform, "ok": True, "publish_id": pid}
        if platform == "instagram":
            rid = instagram.upload_reel(blob["ig_user_id"], blob["access_token"],
                                        public_url, caption)
            return {"platform": platform, "ok": True, "id": rid}
        if platform == "youtube":
            from google.oauth2.credentials import Credentials

            creds = Credentials(
                token=blob["access_token"], refresh_token=blob.get("refresh_token"),
                client_id=settings.YT_CLIENT_ID, client_secret=settings.YT_CLIENT_SECRET,
            )
            vid = yt_client.upload_short(creds, clip_path, title, caption)
            return {"platform": platform, "ok": True, "id": vid}
    except Exception as e:  # noqa: BLE001
        return {"platform": platform, "ok": False, "error": str(e)}
    return {"platform": platform, "ok": False, "error": "unknown platform"}
