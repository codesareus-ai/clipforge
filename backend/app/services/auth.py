"""Self-contained user auth (no external IdP).

- POST /auth/register  -> creates a user, returns a bearer token
- POST /auth/login     -> verifies password (rate-limited), returns a bearer token
- POST /auth/logout    -> revokes the caller's current token (denylist)
- GET  /me             -> returns the caller's user_id (proves the token)

Passwords are hashed with bcrypt (per-password salt + work factor). user_id is a
random UUID, independent of the password. The bearer token is an HMAC-signed
value (itsdangerous) over the user_id. Because tokens are stateless, logout uses
a server-side denylist (revoked_jti) — swapping for Supabase/Auth0 means
replacing get_current_user with the provider's verifier.
"""
from __future__ import annotations

import hashlib
import sqlite3
import time
import uuid
from collections import defaultdict
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

# In-memory login rate limiter: handle -> list of failed timestamps (epoch s).
_FAILED: dict[str, list[float]] = defaultdict(list)
_MAX_FAILS = 5
_WINDOW_S = 300  # 5 minutes


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
    c.execute(
        """CREATE TABLE IF NOT EXISTS revoked_tokens (
            jti TEXT PRIMARY KEY
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


def _jti(token: str) -> str:
    # Stable id for a token without validating it (for denylist lookup).
    return hashlib.sha256(token.encode()).hexdigest()


def revoke_token(token: str) -> None:
    jti = _jti(token)
    with _conn() as c:
        c.execute("INSERT OR IGNORE INTO revoked_tokens(jti) VALUES (?)", (jti,))


def verify_token(token: str) -> str | None:
    # Denylist check first.
    with _conn() as c:
        if c.execute(
            "SELECT 1 FROM revoked_tokens WHERE jti=?", (_jti(token),)
        ).fetchone():
            return None
    try:
        return _signer().loads(token, max_age=60 * 60 * 24 * 30)  # 30d
    except (BadSignature, Exception):
        return None


def _check_rate_limit(handle: str) -> None:
    now = time.time()
    attempts = [t for t in _FAILED[handle] if now - t < _WINDOW_S]
    _FAILED[handle] = attempts
    if len(attempts) >= _MAX_FAILS:
        raise HTTPException(
            status_code=429,
            detail="too many failed logins — try again later",
        )


def _record_failure(handle: str) -> None:
    _FAILED[handle].append(time.time())


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
    _check_rate_limit(handle)
    with _conn() as c:
        row = c.execute(
            "SELECT user_id, pw_hash FROM users WHERE handle=?", (handle,)
        ).fetchone()
    if not row or not _verify_password(password, row[1]):
        _record_failure(handle)
        raise HTTPException(status_code=401, detail="invalid handle or password")
    _FAILED[handle].clear()
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
