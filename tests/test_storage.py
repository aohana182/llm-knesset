"""Tests for conversation storage layer."""
import uuid
import pytest

from backend import storage
from backend.db import db_cursor


def _nuke_conversation(cid):
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM messages WHERE conversation_id = %s", (cid,))
        cur.execute("DELETE FROM conversations WHERE id = %s", (cid,))


class TestStorage:
    def test_create_and_get_conversation(self):
        cid = str(uuid.uuid4())
        uid = str(uuid.uuid4())
        conv = storage.create_conversation(cid, uid)
        assert conv["id"] == cid
        assert conv["title"] == "New Conversation"
        fetched = storage.get_conversation(cid, uid)
        assert fetched is not None
        assert fetched["id"] == cid
        _nuke_conversation(cid)

    def test_get_nonexistent_returns_none(self):
        result = storage.get_conversation(str(uuid.uuid4()), "any-user")
        assert result is None

    def test_get_wrong_user_returns_none(self):
        cid = str(uuid.uuid4())
        uid = str(uuid.uuid4())
        storage.create_conversation(cid, uid)
        result = storage.get_conversation(cid, "wrong-user")
        assert result is None
        _nuke_conversation(cid)

    def test_add_user_message_appears_in_get(self):
        cid = str(uuid.uuid4())
        uid = str(uuid.uuid4())
        storage.create_conversation(cid, uid)
        storage.add_user_message(cid, "Hello world")
        conv = storage.get_conversation(cid, uid)
        assert len(conv["messages"]) == 1
        assert conv["messages"][0]["role"] == "user"
        assert conv["messages"][0]["content"] == "Hello world"
        _nuke_conversation(cid)

    def test_add_assistant_message_appears_in_get(self):
        cid = str(uuid.uuid4())
        uid = str(uuid.uuid4())
        storage.create_conversation(cid, uid)
        storage.add_user_message(cid, "Hi")
        storage.add_assistant_message(
            cid,
            stage1=[{"model": "gpt-4o", "response": "Stage 1 response"}],
            stage2=[{"model": "gpt-4o", "ranking": "FINAL RANKING:\n1. Response A", "parsed_ranking": ["Response A"]}],
            stage3={"model": "gemini", "response": "Final answer"},
        )
        conv = storage.get_conversation(cid, uid)
        assert len(conv["messages"]) == 2
        asst = conv["messages"][1]
        assert asst["role"] == "assistant"
        assert asst["stage3"]["response"] == "Final answer"
        _nuke_conversation(cid)

    def test_update_conversation_title(self):
        cid = str(uuid.uuid4())
        uid = str(uuid.uuid4())
        storage.create_conversation(cid, uid)
        storage.update_conversation_title(cid, "My New Title")
        conv = storage.get_conversation(cid, uid)
        assert conv["title"] == "My New Title"
        _nuke_conversation(cid)

    def test_list_conversations_scoped_to_user(self):
        uid1 = str(uuid.uuid4())
        uid2 = str(uuid.uuid4())
        cid1 = str(uuid.uuid4())
        cid2 = str(uuid.uuid4())
        storage.create_conversation(cid1, uid1)
        storage.create_conversation(cid2, uid2)
        results = storage.list_conversations(uid1)
        ids = [r["id"] for r in results]
        assert cid1 in ids
        assert cid2 not in ids
        _nuke_conversation(cid1)
        _nuke_conversation(cid2)

    def test_list_conversations_includes_message_count(self):
        cid = str(uuid.uuid4())
        uid = str(uuid.uuid4())
        storage.create_conversation(cid, uid)
        storage.add_user_message(cid, "test")
        results = storage.list_conversations(uid)
        match = next((r for r in results if r["id"] == cid), None)
        assert match is not None
        assert match["message_count"] == 1
        _nuke_conversation(cid)
