"""Tests for settings_store and user_store."""
import os
import uuid
import pytest

from backend import settings_store, user_store
from backend.db import db_cursor


def _cleanup_setting(key):
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM settings WHERE key = %s", (key,))


def _cleanup_user(user_id):
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM user_prefs WHERE user_id = %s", (user_id,))


# ── settings_store ────────────────────────────────────────────────────────────

class TestSettingsStore:
    def test_get_missing_key_returns_default(self):
        fake_key = f"__nonexistent_{uuid.uuid4()}"
        result = settings_store._get(fake_key)
        assert result is None

    def test_set_and_get_string(self):
        key = f"__test_{uuid.uuid4()}"
        settings_store._set(key, "hello")
        assert settings_store._get(key) == "hello"
        _cleanup_setting(key)

    def test_set_and_get_list(self):
        key = f"__test_{uuid.uuid4()}"
        settings_store._set(key, ["a", "b", "c"])
        assert settings_store._get(key) == ["a", "b", "c"]
        _cleanup_setting(key)

    def test_overwrite_existing_key(self):
        key = f"__test_{uuid.uuid4()}"
        settings_store._set(key, "first")
        settings_store._set(key, "second")
        assert settings_store._get(key) == "second"
        _cleanup_setting(key)

    def test_get_api_key_falls_back_to_env(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "env-key-123")
        with db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM settings WHERE key = 'openrouter_api_key'")
        result = settings_store.get_api_key()
        assert result == "env-key-123"

    def test_get_council_models_returns_list(self):
        models = settings_store.get_council_models()
        assert isinstance(models, list)
        assert len(models) > 0

    def test_get_chairman_model_returns_string(self):
        chairman = settings_store.get_chairman_model()
        assert isinstance(chairman, str)
        assert len(chairman) > 0

    def test_add_admin_email(self):
        email = f"test-{uuid.uuid4()}@example.com"
        settings_store.add_admin_email(email)
        admins = settings_store.get_admin_emails()
        assert email in admins
        admins.remove(email)
        settings_store._set("admin_emails", admins)

    def test_add_duplicate_admin_email_not_duplicated(self):
        email = f"dup-{uuid.uuid4()}@example.com"
        settings_store.add_admin_email(email)
        settings_store.add_admin_email(email)
        admins = settings_store.get_admin_emails()
        assert admins.count(email) == 1
        admins.remove(email)
        settings_store._set("admin_emails", admins)


# ── user_store ────────────────────────────────────────────────────────────────

class TestUserStore:
    def test_get_prefs_unknown_user_returns_empty(self):
        result = user_store.get_user_prefs("nonexistent-user-xyz")
        assert result == {}

    def test_create_then_get_prefs(self):
        uid = str(uuid.uuid4())
        user_store.update_user_prefs(uid, {"council_models": ["gpt-4o"]})
        result = user_store.get_user_prefs(uid)
        assert result["council_models"] == ["gpt-4o"]
        _cleanup_user(uid)

    def test_update_merges_with_existing(self):
        uid = str(uuid.uuid4())
        user_store.update_user_prefs(uid, {"council_models": ["gpt-4o"]})
        user_store.update_user_prefs(uid, {"chairman_model": "claude"})
        result = user_store.get_user_prefs(uid)
        assert result["council_models"] == ["gpt-4o"]
        assert result["chairman_model"] == "claude"
        _cleanup_user(uid)

    def test_update_overwrites_specific_key(self):
        uid = str(uuid.uuid4())
        user_store.update_user_prefs(uid, {"council_models": ["gpt-4o"]})
        user_store.update_user_prefs(uid, {"council_models": ["claude", "gemini"]})
        result = user_store.get_user_prefs(uid)
        assert result["council_models"] == ["claude", "gemini"]
        _cleanup_user(uid)

    def test_two_users_isolated(self):
        uid1, uid2 = str(uuid.uuid4()), str(uuid.uuid4())
        user_store.update_user_prefs(uid1, {"council_models": ["gpt-4o"]})
        user_store.update_user_prefs(uid2, {"council_models": ["claude"]})
        assert user_store.get_user_prefs(uid1)["council_models"] == ["gpt-4o"]
        assert user_store.get_user_prefs(uid2)["council_models"] == ["claude"]
        _cleanup_user(uid1)
        _cleanup_user(uid2)
