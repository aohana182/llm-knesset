"""PostgreSQL-backed storage for conversations."""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from .db import db_cursor


def create_conversation(conversation_id: str, user_id: str = "") -> Dict[str, Any]:
    now = datetime.utcnow().isoformat()
    with db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO conversations (id, user_id, created_at, title)
            VALUES (%s, %s, %s, %s)
            """,
            (conversation_id, user_id, now, "New Conversation"),
        )
    return {
        "id": conversation_id,
        "user_id": user_id,
        "created_at": now,
        "title": "New Conversation",
        "messages": [],
    }


def get_conversation(conversation_id: str, user_id: str = "") -> Optional[Dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute(
            "SELECT id, user_id, created_at, title FROM conversations WHERE id = %s",
            (conversation_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        row = dict(row)
        if user_id and row["user_id"] and row["user_id"] != user_id:
            return None

        cur.execute(
            "SELECT role, content FROM messages WHERE conversation_id = %s ORDER BY created_at, id",
            (conversation_id,),
        )
        msg_rows = cur.fetchall()

    messages = []
    for m in msg_rows:
        content = m["content"]
        if isinstance(content, str):
            content = json.loads(content)
        if m["role"] == "user":
            messages.append({"role": "user", "content": content.get("text", "")})
        else:
            messages.append({"role": "assistant", **content})

    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else row["created_at"],
        "title": row["title"],
        "messages": messages,
    }


def list_conversations(user_id: str = "") -> List[Dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute(
            """
            SELECT c.id, c.created_at, c.title,
                   COUNT(m.id) AS message_count
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            WHERE c.user_id = %s
            GROUP BY c.id
            ORDER BY c.created_at DESC
            """,
            (user_id,),
        )
        rows = cur.fetchall()

    return [
        {
            "id": r["id"],
            "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else r["created_at"],
            "title": r["title"],
            "message_count": r["message_count"],
        }
        for r in rows
    ]


def add_user_message(conversation_id: str, content: str):
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s)",
            (conversation_id, "user", json.dumps({"text": content})),
        )


def add_assistant_message(
    conversation_id: str,
    stage1: List[Dict[str, Any]],
    stage2: List[Dict[str, Any]],
    stage3: Dict[str, Any],
):
    with db_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO messages (conversation_id, role, content) VALUES (%s, %s, %s)",
            (
                conversation_id,
                "assistant",
                json.dumps({"stage1": stage1, "stage2": stage2, "stage3": stage3}),
            ),
        )


def update_conversation_title(conversation_id: str, title: str):
    with db_cursor(commit=True) as cur:
        cur.execute(
            "UPDATE conversations SET title = %s WHERE id = %s",
            (title, conversation_id),
        )
