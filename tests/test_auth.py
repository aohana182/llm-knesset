"""Tests for session token creation and verification."""
import os
import time
import pytest

os.environ.setdefault("SESSION_SECRET", "test-secret-for-testing-only")

from backend.auth import create_session_token, verify_session_token


class TestSessionToken:
    def _user(self):
        return {"sub": "user123", "email": "a@b.com", "name": "Alice", "picture": ""}

    def test_round_trip(self):
        user = self._user()
        token = create_session_token(user)
        result = verify_session_token(token)
        assert result is not None
        assert result["sub"] == "user123"
        assert result["email"] == "a@b.com"

    def test_tampered_signature_rejected(self):
        token = create_session_token(self._user())
        bad = token[:-4] + "xxxx"
        assert verify_session_token(bad) is None

    def test_tampered_payload_rejected(self):
        import base64, json
        token = create_session_token(self._user())
        b64, sig = token.rsplit(".", 1)
        data = json.loads(base64.urlsafe_b64decode(b64 + "=="))
        data["email"] = "hacker@evil.com"
        new_b64 = base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")
        assert verify_session_token(f"{new_b64}.{sig}") is None

    def test_expired_token_rejected(self, monkeypatch):
        import backend.auth as auth_module
        original_time = time.time
        monkeypatch.setattr(time, "time", lambda: original_time() - 999999)
        token = create_session_token(self._user())
        monkeypatch.setattr(time, "time", original_time)
        assert verify_session_token(token) is None

    def test_empty_string_rejected(self):
        assert verify_session_token("") is None

    def test_garbage_rejected(self):
        assert verify_session_token("not.a.valid.token.at.all") is None

    def test_different_secrets_incompatible(self, monkeypatch):
        monkeypatch.setenv("SESSION_SECRET", "secret-A")
        token = create_session_token(self._user())
        monkeypatch.setenv("SESSION_SECRET", "secret-B")
        assert verify_session_token(token) is None
