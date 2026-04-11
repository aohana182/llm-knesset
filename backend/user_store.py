"""PostgreSQL-backed per-user preference storage for LLM Knesset."""

import json
from typing import Any, Dict
from .db import db_cursor


def get_user_prefs(user_id: str) -> Dict[str, Any]:
    with db_cursor() as cur:
        cur.execute("SELECT prefs FROM user_prefs WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
    if row is None:
        return {}
    prefs = row["prefs"]
    if isinstance(prefs, str):
        try:
            return json.loads(prefs)
        except Exception:
            return {}
    return dict(prefs) if prefs else {}


def update_user_prefs(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    prefs = get_user_prefs(user_id)
    prefs.update(updates)
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO user_prefs (user_id, prefs) VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET prefs = EXCLUDED.prefs
            """,
            (user_id, json.dumps(prefs)),
        )
    return prefs
