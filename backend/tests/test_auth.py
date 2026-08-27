"""Auth tests: registration, login, logout revocation, rate-limit, password isolation."""
import os
import tempfile
from pathlib import Path

import pytest

from app.services import auth as auth_mod
from app.services.auth import authenticate, issue_token, register_user, verify_token
from app.services.auth import _verify_password, _hash_password


@pytest.fixture(autouse=True)
def isolated_db():
    # Throwaway DB per test (avoids Windows file-lock collisions on clipforge.db).
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    auth_mod._DB = Path(path)
    yield


@pytest.fixture(autouse=True)
def token_secret():
    auth_mod.settings.TOKEN_SECRET = "test-secret-for-auth-tests"
    yield
    auth_mod.settings.TOKEN_SECRET = None


def test_register_then_login():
    tok = register_user("alice", "sup3rsecret")
    assert verify_token(tok)
    login_tok = authenticate("alice", "sup3rsecret")
    assert verify_token(login_tok)


def test_wrong_password_rejected():
    register_user("bob", "rightpass")
    with pytest.raises(Exception):  # HTTPException 401
        authenticate("bob", "wrongpass")


def test_duplicate_handle_rejected():
    register_user("carol", "pw1")
    with pytest.raises(Exception):  # HTTPException 409
        register_user("carol", "pw2")


def test_logout_revokes_token():
    tok = register_user("dave", "pw")
    assert verify_token(tok)
    # Simulate the logout route: it revokes the presented token.
    auth_mod.revoke_token(tok)
    assert verify_token(tok) is None


def test_login_rate_limit():
    register_user("erin", "pw")
    # 5 wrong attempts -> 6th raises 429 (too many failed logins).
    for _ in range(5):
        with pytest.raises(Exception):
            authenticate("erin", "wrong")
    with pytest.raises(Exception) as e:
        authenticate("erin", "wrong")
    assert "429" in str(e.value) or "too many" in str(e.value).lower()


def test_password_not_stored_plaintext():
    h = _hash_password("hunter2")
    assert "hunter2" not in h
    assert _verify_password("hunter2", h)
    assert not _verify_password("nope", h)
