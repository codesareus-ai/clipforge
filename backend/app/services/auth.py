"""Self-contained user auth (no external IdP).

- POST /auth/register  -> creates a user, returns a bearer token
- POST /auth/login     -> verifies password, returns a bearer token
- GET  /me             -> returns the caller's user_id (proves the token)

Passwords are hashed with bcrypt (per-password salt + work factor), not a raw
SHA-256. user_id is a random UUID, independent of the password, so a password
change never alters identity. The token is an HMAC-signed value (itsdangerous)
over the user_id. Swap this file for Supabase/Auth0 by replacing
`get_current_user` with the provider's verifier — the rest of the app only
depends on it returning a `user_id` string.
"""
from __future__ import annotations

import hashlib
import sqlite3
import uuid
from pathlib import Path

import bcrypt
from fastapi import Depends, HTTPException
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


def _hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def _verify_password(pw: str, pw_hash: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), pw_hash.encode())
    except ValueError:
        return False


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
    user_id = uuid.uuid4().hex
    with _conn() as c:
        try:
            c.execute(
                "INSERT INTO users(user_id, handle, pw_hash) VALUES (?, ?, ?)",
                (user_id, handle, _hash_password(password)),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="handle already registered")
    return issue_token(user_id)


def authenticate(handle: str, password: str) -> str:
    with _conn() as c:
        row = c.execute(
            "SELECT user_id, pw_hash FROM users WHERE handle=?", (handle,)
        ).fetchone()
    if not row or not _verify_password(password, row[1]):
        raise HTTPException(status_code=401, detail="invalid handle or password")
    return issue_token(row[0])


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


class LoginReq(BaseModel):
    handle: str
    password: str
