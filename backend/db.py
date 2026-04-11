"""PostgreSQL connection pool for LLM Knesset."""

import os
import logging
import psycopg2
import psycopg2.pool
from psycopg2 import OperationalError
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

_pool = None

_KEEPALIVE_KWARGS = {
    "keepalives": 1,
    "keepalives_idle": 30,
    "keepalives_interval": 10,
    "keepalives_count": 5,
}

_MAX_RETRIES = 3


def _make_pool():
    return psycopg2.pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=10,
        dsn=os.environ["DATABASE_URL"],
        **_KEEPALIVE_KWARGS,
    )


def get_pool():
    global _pool
    if _pool is None or _pool.closed:
        _pool = _make_pool()
    return _pool


def _discard_conn(conn):
    """Return a broken connection to the pool with close=True so it is destroyed."""
    try:
        get_pool().putconn(conn, close=True)
    except Exception:
        try:
            conn.close()
        except Exception:
            pass


class db_cursor:
    """Context manager that borrows a connection from the pool and returns it.

    Retries up to _MAX_RETRIES times if the pooled connection is stale/closed,
    discarding each bad connection before fetching a fresh one.
    """

    def __init__(self, commit=False):
        self.commit = commit
        self.conn = None
        self.cur = None

    def __enter__(self):
        p = get_pool()
        last_err = None
        for attempt in range(_MAX_RETRIES):
            conn = p.getconn()
            try:
                if conn.closed:
                    raise OperationalError("connection is closed")
                cur = conn.cursor(cursor_factory=RealDictCursor)
                cur.execute("SELECT 1")
                cur.fetchone()
                self.conn = conn
                self.cur = conn.cursor(cursor_factory=RealDictCursor)
                return self.cur
            except OperationalError as e:
                last_err = e
                logger.warning(
                    "Stale connection on attempt %d/%d, discarding: %s",
                    attempt + 1,
                    _MAX_RETRIES,
                    e,
                )
                _discard_conn(conn)
        raise last_err

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn is None:
            return False
        try:
            if exc_type is None and self.commit:
                self.conn.commit()
            else:
                self.conn.rollback()
        except OperationalError as e:
            logger.warning("Commit/rollback failed on broken connection, discarding: %s", e)
            _discard_conn(self.conn)
            self.conn = None
            return False
        finally:
            if self.cur is not None:
                try:
                    self.cur.close()
                except Exception:
                    pass
        if self.conn is not None:
            get_pool().putconn(self.conn)
        return False
