"""Encrypted token vault. Stores OAuth tokens per (user, platform).

PROD NOTE: this uses a local SQLite file for the encrypted blobs. In production
swap the storage for your DB (Postgres) but keep the Fernet envelope encryption
— never store plaintext tokens. Refresh tokens rotate on every refresh; persist
the NEW refresh token each time or the user must re-authorize.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from cryptography.fernet import Fernet

from app.config import get_settings

settings = get_settings()
_DB = Path("./vault.db")


def _fernet() -> Fernet:
    if not settings.TOKEN_ENCRYPTION_KEY:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY not set (generate with Fernet.generate_key())")
    return Fernet(settings.TOKEN_ENCRYPTION_KEY.encode())


def _conn() -> sqlite3.Connection:
    _DB.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(_DB)
    c.execute(
        """CREATE TABLE IF NOT EXISTS tokens (
            key TEXT PRIMARY KEY, blob TEXT
        )"""
    )
    return c


def save_token(user_id: str, platform: str, token_json: str) -> None:
    key = f"{user_id}:{platform}"
    blob = _fernet().encrypt(token_json.encode()).decode()
    with _conn() as c:
        c.execute("REPLACE INTO tokens(key, blob) VALUES (?, ?)", (key, blob))


def load_token(user_id: str, platform: str) -> str | None:
    with _conn() as c:
        row = c.execute("SELECT blob FROM tokens WHERE key=?", (f"{user_id}:{platform}",)).fetchone()
    if not row:
        return None
    return _fernet().decrypt(row[0].encode()).decode()


def delete_token(user_id: str, platform: str) -> None:
    with _conn() as c:
        c.execute("DELETE FROM tokens WHERE key=?", (f"{user_id}:{platform}",))
