"""Auth tests: registration, login, token verification, password isolation."""
import os
import tempfile
from pathlib import Path

import pytest

from app.services import auth as auth_mod
from app.services.auth import authenticate, register_user, verify_token
from app.services.auth import _verify_password, _hash_password


@pytest.fixture(autouse=True)
def isolated_db():
    # Use a throwaway DB for auth tests so each test starts clean and we never
    # fight Windows file locking on the shared clipforge.db. We intentionally
    # do NOT delete on teardown — SQLite keeps the file open via auth_mod's
    # connection, and Windows raises PermissionError on delete-while-open.
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.remove(path)
    auth_mod._DB = Path(path)
    yield


def test_register_then_login():
    handle, pw = "alice", "sup3rsecret"
    tok = register_user(handle, pw)
    assert verify_token(tok)  # token valid
    login_tok = authenticate(handle, pw)
    assert verify_token(login_tok)


def test_wrong_password_rejected():
    register_user("bob", "rightpass")
    with pytest.raises(Exception):  # HTTPException 401
        authenticate("bob", "wrongpass")


def test_duplicate_handle_rejected():
    register_user("carol", "pw1")
    with pytest.raises(Exception):  # HTTPException 409
        register_user("carol", "pw2")


def test_password_not_stored_plaintext():
    h = _hash_password("hunter2")
    assert "hunter2" not in h
    assert _verify_password("hunter2", h)
    assert not _verify_password("nope", h)
