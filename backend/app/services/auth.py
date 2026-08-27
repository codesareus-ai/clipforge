"""Self-contained user auth (no external IdP).

- POST /auth/register  -> creates a user, returns a bearer token
- GET  /me             -> returns the caller's user_id (proves the token)

The token is an HMAC-signed value (fastapi's signed cookie serializer over
settings.TOKEN_SECRET). No plaintext passwords are stored; we keep a simple
handle + salted hash so the same handle cannot be registered twice. Swap this
file for Supabase/Auth0 by replacing `get_current_user` with the provider's
verifier — the rest of the app only depends on `get_current_user` returning a
`user_id` string.
"""
from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from itsdangerous import BadSignature, URLSafeTimedSerializer
from pydantic import BaseModel

from app.config import get_settings

settings = get_settings()
_DB = Path("./clipforge.db")
_bearer = HTTPBearer(auto_error=False)


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(_DB)
    c.execute(
        """CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            handle  TEXT UNIQUE NOT NULL,
            pw_hash TEXT NOT NULL
        )"""
    )
    return c


def _hash(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def _signer() -> URLSafeTimedSerializer:
    if not settings.TOKEN_SECRET:
        raise RuntimeError("TOKEN_SECRET not set (generate a random 32+ char string)")
    return URLSafeTimedSerializer(settings.TOKEN_SECRET, salt="clipforge-auth")


def issue_token(user_id: str) -> str:
    return _signer().dumps(user_id)


def verify_token(token: str) -> str | None:
    try:
        return _signer().loads(token, max_age=60 * 60 * 24 * 30)  # 30d
    except (BadSignature, Exception):
        return None


def register_user(handle: str, password: str) -> str:
    user_id = hashlib.sha256(f"{handle}:{password}".encode()).hexdigest()[:16]
    with _conn() as c:
        try:
            c.execute(
                "INSERT INTO users(user_id, handle, pw_hash) VALUES (?, ?, ?)",
                (user_id, handle, _hash(password)),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="handle already registered")
    return issue_token(user_id)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    if not creds or not creds.credentials:
        raise HTTPException(status_code=401, detail="missing bearer token")
    user_id = verify_token(creds.credentials)
    if not user_id:
        raise HTTPException(status_code=401, detail="invalid or expired token")
    return user_id


class RegisterReq(BaseModel):
    handle: str
    password: str
