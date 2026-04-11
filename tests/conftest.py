"""Shared fixtures for LLM Knesset tests."""
import os
import pytest
import uuid

os.environ.setdefault("SESSION_SECRET", "test-secret-for-testing-only")
os.environ.setdefault("DATABASE_URL", os.environ.get("DATABASE_URL", ""))

from backend.auth import create_session_token

def make_user(email="user@example.com", sub=None, name="Test User"):
    return {
        "sub": sub or str(uuid.uuid4()),
        "email": email,
        "name": name,
        "picture": "",
    }

def make_admin_user():
    return make_user(email="admin@example.com", sub="admin-sub-fixed")

@pytest.fixture
def user():
    return make_user()

@pytest.fixture
def admin_user():
    return make_admin_user()

@pytest.fixture
def user_token(user):
    return create_session_token(user)

@pytest.fixture
def admin_token(admin_user):
    return create_session_token(admin_user)
