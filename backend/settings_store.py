"""PostgreSQL-backed settings storage for LLM Knesset."""

import json
import os
from typing import Any, Dict, List
from .db import db_cursor

_DEFAULTS: Dict[str, Any] = {
    "openrouter_api_key": "",
    "council_models": [
        "openai/gpt-4o",
        "google/gemini-pro",
        "anthropic/claude-3-5-sonnet",
        "x-ai/grok-2",
    ],
    "chairman_model": "google/gemini-pro",
    "admin_emails": [],
}


def _get(key: str) -> Any:
    with db_cursor() as cur:
        cur.execute("SELECT value FROM settings WHERE key = %s", (key,))
        row = cur.fetchone()
    if row is None:
        return _DEFAULTS.get(key)
    try:
        return json.loads(row["value"])
    except (json.JSONDecodeError, TypeError):
        return row["value"]


def _set(key: str, value: Any) -> None:
    serialized = json.dumps(value)
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO settings (key, value) VALUES (%s, %s)
            ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
            """,
            (key, serialized),
        )


def get_settings() -> Dict[str, Any]:
    result = {}
    for key, default in _DEFAULTS.items():
        result[key] = _get(key) or default
    env_key = os.getenv("OPENROUTER_API_KEY", "")
    if not result.get("openrouter_api_key") and env_key:
        result["openrouter_api_key"] = env_key
    return result


def update_settings(updates: Dict[str, Any]) -> Dict[str, Any]:
    allowed = set(_DEFAULTS.keys())
    for k, v in updates.items():
        if k in allowed:
            _set(k, v)
    return get_settings()


def get_api_key() -> str:
    key = _get("openrouter_api_key") or ""
    if not key:
        key = os.getenv("OPENROUTER_API_KEY", "")
    return key


def get_council_models() -> List[str]:
    return _get("council_models") or _DEFAULTS["council_models"]


def get_chairman_model() -> str:
    return _get("chairman_model") or _DEFAULTS["chairman_model"]


def get_admin_emails() -> List[str]:
    env_admins = os.getenv("ADMIN_EMAILS", "")
    if env_admins:
        return [e.strip() for e in env_admins.split(",") if e.strip()]
    return _get("admin_emails") or []


def add_admin_email(email: str) -> None:
    admins = get_admin_emails()
    if email not in admins:
        admins.append(email)
        _set("admin_emails", admins)
