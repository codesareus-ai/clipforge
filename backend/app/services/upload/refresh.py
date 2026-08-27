"""Refresh OAuth tokens. TikTok refresh tokens ROTATE on every call, so the
new refresh token must be persisted. Run periodically (cron / APScheduler)."""
from __future__ import annotations

import json

import requests

from app.config import get_settings
from app.services.upload.vault import load_token, save_token

settings = get_settings()


def refresh_platform(user_id: str, platform: str) -> dict | None:
    raw = load_token(user_id, platform)
    if not raw:
        return None
    blob = json.loads(raw)
    if platform == "tiktok":
        r = requests.post("https://open.tiktokapis.com/v2/oauth/token/", data={
            "client_key": settings.TIKTOK_CLIENT_KEY,
            "client_secret": settings.TIKTOK_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": blob["refresh_token"],
        }, timeout=30).json()
        # TikTok rotates BOTH tokens — persist the new pair
        blob = {**blob, "access_token": r["access_token"], "refresh_token": r["refresh_token"]}
    elif platform == "instagram":
        r = requests.get("https://graph.facebook.com/v18.0/oauth/access_token", params={
            "grant_type": "fb_exchange_token",
            "client_id": settings.IG_APP_ID,
            "client_secret": settings.IG_APP_SECRET,
            "fb_exchange_token": blob["access_token"],
        }, timeout=30).json()
        blob = {**blob, "access_token": r["access_token"]}
    elif platform == "youtube":
        r = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": settings.YT_CLIENT_ID,
            "client_secret": settings.YT_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": blob["refresh_token"],
        }, timeout=30).json()
        blob = {**blob, "access_token": r["access_token"]}
    else:
        return None
    save_token(user_id, platform, json.dumps(blob))
    return blob


def refresh_user_tokens(user_id: str, platforms=("tiktok", "instagram", "youtube")) -> dict:
    return {p: refresh_platform(user_id, p) for p in platforms}
