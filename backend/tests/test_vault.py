import json

from cryptography.fernet import Fernet

from app.services.upload import vault


def test_roundtrip(tmp_path, monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(vault.settings, "TOKEN_ENCRYPTION_KEY", key)
    monkeypatch.setattr(vault, "_DB", tmp_path / "vault.db")

    vault.save_token("u1", "tiktok", json.dumps({"a": 1}))
    assert json.loads(vault.load_token("u1", "tiktok"))["a"] == 1
    assert vault.load_token("u2", "tiktok") is None  # no token -> None
