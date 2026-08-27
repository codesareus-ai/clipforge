"""One-time setup: generate backend/.env from .env.example with secure secrets.

Run:  python setup_env.py
It copies backend/.env.example -> backend/.env and fills in:
  TOKEN_SECRET            (random 32+ char string)
  TOKEN_ENCRYPTION_KEY    (Fernet key)
Any pre-existing values in backend/.env are preserved (not overwritten).
"""
from __future__ import annotations

import re
from pathlib import Path

import secrets

try:
    from cryptography.fernet import Fernet
except ImportError:
    Fernet = None  # only needed to generate a key; install via requirements-dev if missing

ROOT = Path(__file__).resolve().parent
EXAMPLE = ROOT / "backend" / ".env.example"
OUT = ROOT / "backend" / ".env"


def gen_secret(n: int = 48) -> str:
    return secrets.token_urlsafe(n)


def gen_fernet() -> str:
    if Fernet is None:
        return ""  # placeholder; pip install cryptography to generate
    return Fernet.generate_key().decode()


def main() -> None:
    if not EXAMPLE.exists():
        raise SystemExit(f"missing {EXAMPLE}")
    text = EXAMPLE.read_text()

    if OUT.exists():
        existing = OUT.read_text()
        print(f"{OUT} already exists — preserving existing values, only filling blanks.")
    else:
        existing = ""

    existing_keys = set(re.findall(r"^([A-Z_]+)=", existing, re.MULTILINE))

    def fill(key: str, value: str) -> str:
        nonlocal text
        if key in existing_keys:
            return  # keep user's existing value
        pattern = rf"^{key}=.*$"
        if re.search(pattern, text, re.MULTILINE):
            text = re.sub(pattern, f"{key}={value}", text, flags=re.MULTILINE)
        else:
            text += f"\n{key}={value}\n"
        return

    fill("TOKEN_SECRET", gen_secret())
    if Fernet is not None:
        fill("TOKEN_ENCRYPTION_KEY", gen_fernet())

    OUT.write_text(text)
    print(f"Wrote {OUT}")
    print("Edit it to add your platform OAuth keys + S3 creds, then: docker compose up --build")


if __name__ == "__main__":
    main()
