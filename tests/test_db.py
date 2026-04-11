"""Tests for the DB connection pool and context manager."""
import os
import pytest
import psycopg2

from backend.db import db_cursor, _discard_conn, get_pool


class TestDbCursor:
    def test_basic_query_works(self):
        with db_cursor() as cur:
            cur.execute("SELECT 1 AS val")
            row = cur.fetchone()
        assert row["val"] == 1

    def test_commit_persists_data(self):
        import uuid
        unique = str(uuid.uuid4())
        with db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO settings (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                (f"__test_{unique}", f'"{unique}"'),
            )
        with db_cursor() as cur:
            cur.execute("SELECT value FROM settings WHERE key = %s", (f"__test_{unique}",))
            row = cur.fetchone()
        assert row is not None
        assert unique in row["value"]
        with db_cursor(commit=True) as cur:
            cur.execute("DELETE FROM settings WHERE key = %s", (f"__test_{unique}",))

    def test_no_commit_rolls_back(self):
        import uuid
        unique = str(uuid.uuid4())
        with db_cursor() as cur:
            cur.execute(
                "INSERT INTO settings (key, value) VALUES (%s, %s)",
                (f"__test_{unique}", '"rollback"'),
            )
        with db_cursor() as cur:
            cur.execute("SELECT value FROM settings WHERE key = %s", (f"__test_{unique}",))
            row = cur.fetchone()
        assert row is None

    def test_exception_in_block_triggers_rollback(self):
        import uuid
        unique = str(uuid.uuid4())
        try:
            with db_cursor(commit=True) as cur:
                cur.execute(
                    "INSERT INTO settings (key, value) VALUES (%s, %s)",
                    (f"__test_{unique}", '"should_rollback"'),
                )
                raise RuntimeError("deliberate error")
        except RuntimeError:
            pass
        with db_cursor() as cur:
            cur.execute("SELECT value FROM settings WHERE key = %s", (f"__test_{unique}",))
            row = cur.fetchone()
        assert row is None

    def test_stale_connection_discarded_and_retried(self):
        pool = get_pool()
        conn = pool.getconn()
        conn.close()
        pool.putconn(conn)
        with db_cursor() as cur:
            cur.execute("SELECT 2 AS val")
            row = cur.fetchone()
        assert row["val"] == 2

    def test_multiple_concurrent_cursors(self):
        results = []
        for i in range(5):
            with db_cursor() as cur:
                cur.execute("SELECT %s AS n", (i,))
                results.append(cur.fetchone()["n"])
        assert results == [0, 1, 2, 3, 4]
