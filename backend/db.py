"""PostgreSQL connection pool for LLM Knesset."""

import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

_pool = None


def get_pool():
    global _pool
    if _pool is None:
        _pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=os.environ["DATABASE_URL"],
        )
    return _pool


def get_conn():
    return get_pool().getconn()


def put_conn(conn):
    get_pool().putconn(conn)


class db_cursor:
    """Context manager that borrows a connection from the pool and returns it."""

    def __init__(self, commit=False):
        self.commit = commit
        self.conn = None
        self.cur = None

    def __enter__(self):
        self.conn = get_conn()
        self.cur = self.conn.cursor(cursor_factory=RealDictCursor)
        return self.cur

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None and self.commit:
            self.conn.commit()
        else:
            self.conn.rollback()
        self.cur.close()
        put_conn(self.conn)
        return False
