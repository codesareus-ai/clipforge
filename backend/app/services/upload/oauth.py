"""OAuth onboarding for TikTok / Instagram / YouTube.

Flow per platform:
- GET /auth/{platform}/login  -> 302 to provider authorize URL (state = "user_id:rand")
- provider -> GET /auth/{platform}/callback?code=...&state=...
- exchange_code() trades code for tokens, stores them encrypted in the vault
  keyed by (user_id, platform). Blobs include platform-specific ids
  (open_id for TikTok, ig_user_id for IG, refresh_token for YouTube).
"""
from __future__ import annotations

import json
import secrets
from urllib.parse import urlencode

import requests

from app.config import get_settings
from app.services.upload.vault import save_token

settings = get_settings()


def build_authorize_url(platform: str, user_id: str, redirect_uri: str) -> str:
    state = f"{user_id}:{secrets.token_urlsafe(8)}"
    if platform == "tiktok":
        return "https://www.tiktok.com/v2/auth/authorize/?" + urlencode({
            "client_key": settings.TIKTOK_CLIENT_KEY,
            "scope": "video.upload",
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "state": state,
        })
    if platform == "instagram":
        return "https://www.facebook.com/v18.0/dialog/oauth?" + urlencode({
            "client_id": settings.IG_APP_ID,
            "redirect_uri": redirect_uri,
            "scope": "instagram_basic,instagram_content_publish,pages_read_engagement",
            "response_type": "code",
            "state": state,
        })
    if platform == "youtube":
        return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
            "client_id": settings.YT_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "scope": "https://www.googleapis.com/auth/youtube.upload",
            "response_type": "code",
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        })
    raise ValueError(f"unknown platform {platform}")


def exchange_code(platform: str, user_id: str, code: str, redirect_uri: str) -> dict:
    """Exchange an OAuth code for tokens; store via vault. Returns the stored blob."""
    if platform == "tiktok":
        r = requests.post("https://open.tiktokapis.com/v2/oauth/token/", data={
            "client_key": settings.TIKTOK_CLIENT_KEY,
            "client_secret": settings.TIKTOK_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }, timeout=30).json()
        blob = {"access_token": r["access_token"], "refresh_token": r["refresh_token"],
                "expires_in": r["expires_in"], "open_id": r["open_id"]}
    elif platform == "instagram":
        short = requests.get("https://graph.facebook.com/v18.0/oauth/access_token", params={
            "client_id": settings.IG_APP_ID,
            "client_secret": settings.IG_APP_SECRET,
            "redirect_uri": redirect_uri,
            "code": code,
        }, timeout=30).json()
        long = requests.get("https://graph.facebook.com/v18.0/oauth/access_token", params={
            "grant_type": "fb_exchange_token",
            "client_id": settings.IG_APP_ID,
            "client_secret": settings.IG_APP_SECRET,
            "fb_exchange_token": short["access_token"],
        }, timeout=30).json()
        blob = {"access_token": long["access_token"],
                "ig_user_id": _ig_user_id(long["access_token"]),
                "expires_in": long.get("expires_in")}
    elif platform == "youtube":
        r = requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": settings.YT_CLIENT_ID,
            "client_secret": settings.YT_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        }, timeout=30).json()
        blob = {"access_token": r["access_token"], "refresh_token": r.get("refresh_token"),
                "expires_in": r.get("expires_in")}
    else:
        raise ValueError(f"unknown platform {platform}")
    save_token(user_id, platform, json.dumps(blob))
    return blob


def _ig_user_id(token: str) -> str:
    pages = requests.get("https://graph.facebook.com/v18.0/me/accounts",
                         params={"access_token": token}, timeout=30).json()
    page = (pages.get("data") or [{}])[0]
    ig = requests.get(f"https://graph.facebook.com/v18.0/{page['id']}",
                      params={"fields": "instagram_business_account",
                              "access_token": token}, timeout=30).json()
    return ig["instagram_business_account"]["id"]
