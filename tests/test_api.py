"""Tests for FastAPI endpoints using TestClient with auth overrides."""
import os
import uuid
import json
import pytest

os.environ.setdefault("SESSION_SECRET", "test-secret-for-testing-only")

from fastapi.testclient import TestClient
from backend.main import app
from backend import auth, settings_store
from backend.db import db_cursor


def _make_user(email="user@test.com", sub=None):
    return {"sub": sub or str(uuid.uuid4()), "email": email, "name": "Tester", "picture": ""}

def _make_admin():
    return _make_user(email="admin@test.com", sub="admin-api-test-sub")

def _client_as(user):
    app.dependency_overrides[auth.require_user] = lambda: user
    app.dependency_overrides[auth.require_admin] = lambda: user
    return TestClient(app)

def _client_unauthed():
    app.dependency_overrides.clear()
    return TestClient(app)

def _client_user_not_admin(user):
    app.dependency_overrides[auth.require_user] = lambda: user
    app.dependency_overrides[auth.require_admin] = auth.require_admin
    return TestClient(app)


# ── Auth guards ───────────────────────────────────────────────────────────────

class TestAuthGuards:
    def test_me_unauthenticated(self):
        client = _client_unauthed()
        r = client.get("/api/me")
        assert r.status_code == 401

    def test_conversations_unauthenticated(self):
        client = _client_unauthed()
        r = client.get("/api/conversations")
        assert r.status_code == 401

    def test_settings_unauthenticated(self):
        client = _client_unauthed()
        r = client.get("/api/settings")
        assert r.status_code == 401

    def test_prefs_unauthenticated(self):
        client = _client_unauthed()
        r = client.get("/api/prefs")
        assert r.status_code == 401


# ── /api/me ───────────────────────────────────────────────────────────────────

class TestMe:
    def test_returns_user_fields(self):
        user = _make_user()
        client = _client_as(user)
        r = client.get("/api/me")
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == user["email"]
        assert data["name"] == user["name"]
        assert "is_admin" in data

    def test_admin_flag_true_for_admin(self):
        admin = _make_admin()
        settings_store.add_admin_email(admin["email"])
        client = _client_as(admin)
        r = client.get("/api/me")
        assert r.status_code == 200
        assert r.json()["is_admin"] is True

    def test_admin_flag_false_for_regular_user(self):
        user = _make_user(email=f"notadmin-{uuid.uuid4()}@test.com")
        client = _client_as(user)
        r = client.get("/api/me")
        assert r.status_code == 200
        assert r.json()["is_admin"] is False


# ── /api/conversations ────────────────────────────────────────────────────────

class TestConversations:
    def _cleanup(self, cid):
        with db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM messages WHERE conversation_id = %s", (cid,))
            cur.execute("DELETE FROM conversations WHERE id = %s", (cid,))

    def test_create_conversation(self):
        user = _make_user()
        client = _client_as(user)
        r = client.post("/api/conversations", json={})
        assert r.status_code == 200
        data = r.json()
        assert "id" in data
        assert data["title"] == "New Conversation"
        self._cleanup(data["id"])

    def test_get_conversation(self):
        user = _make_user()
        client = _client_as(user)
        created = client.post("/api/conversations", json={}).json()
        r = client.get(f"/api/conversations/{created['id']}")
        assert r.status_code == 200
        assert r.json()["id"] == created["id"]
        self._cleanup(created["id"])

    def test_get_nonexistent_conversation_404(self):
        user = _make_user()
        client = _client_as(user)
        r = client.get(f"/api/conversations/{uuid.uuid4()}")
        assert r.status_code == 404

    def test_list_conversations_returns_own_only(self):
        user1 = _make_user()
        user2 = _make_user()
        c1 = _client_as(user1).post("/api/conversations", json={}).json()
        c2 = _client_as(user2).post("/api/conversations", json={}).json()
        listed = _client_as(user1).get("/api/conversations").json()
        ids = [c["id"] for c in listed]
        assert c1["id"] in ids
        assert c2["id"] not in ids
        self._cleanup(c1["id"])
        self._cleanup(c2["id"])

    def test_list_response_shape(self):
        user = _make_user()
        client = _client_as(user)
        c = client.post("/api/conversations", json={}).json()
        listed = client.get("/api/conversations").json()
        match = next((x for x in listed if x["id"] == c["id"]), None)
        assert match is not None
        assert "title" in match
        assert "created_at" in match
        assert "message_count" in match
        self._cleanup(c["id"])


# ── /api/prefs ────────────────────────────────────────────────────────────────

class TestPrefs:
    def test_get_prefs_returns_defaults_for_new_user(self):
        user = _make_user()
        client = _client_as(user)
        r = client.get("/api/prefs")
        assert r.status_code == 200
        data = r.json()
        assert "council_models" in data
        assert "chairman_model" in data
        assert "using_defaults" in data

    def test_update_and_get_prefs(self):
        user = _make_user()
        client = _client_as(user)
        r = client.put("/api/prefs", json={"council_models": ["gpt-4o", "claude"], "chairman_model": "gemini"})
        assert r.status_code == 200
        r2 = client.get("/api/prefs")
        data = r2.json()
        assert data["council_models"] == ["gpt-4o", "claude"]
        assert data["chairman_model"] == "gemini"
        assert data["using_defaults"] is False
        with db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM user_prefs WHERE user_id = %s", (user["sub"],))


# ── /api/settings (admin only) ────────────────────────────────────────────────

class TestSettings:
    def test_get_settings_as_admin(self):
        admin = _make_admin()
        settings_store.add_admin_email(admin["email"])
        client = _client_as(admin)
        r = client.get("/api/settings")
        assert r.status_code == 200
        data = r.json()
        assert "council_models" in data
        assert "chairman_model" in data
        assert "openrouter_api_key_set" in data

    def test_api_key_masked_in_response(self):
        admin = _make_admin()
        settings_store.add_admin_email(admin["email"])
        settings_store._set("openrouter_api_key", "sk-abcdefgh1234")
        client = _client_as(admin)
        r = client.get("/api/settings")
        preview = r.json().get("openrouter_api_key_preview", "")
        assert "sk-abcdefgh" not in preview
        assert "1234" in preview

    def test_update_settings_as_admin(self):
        admin = _make_admin()
        settings_store.add_admin_email(admin["email"])
        client = _client_as(admin)
        r = client.put("/api/settings", json={"council_models": ["gpt-4o"]})
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_test_connection_no_key(self, monkeypatch):
        admin = _make_admin()
        settings_store.add_admin_email(admin["email"])
        settings_store._set("openrouter_api_key", "")
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        client = _client_as(admin)
        r = client.post("/api/settings/test")
        assert r.status_code == 200
        assert r.json()["success"] is False
