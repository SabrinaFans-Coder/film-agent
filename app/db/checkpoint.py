import asyncio
import json
import sqlite3
from contextlib import AsyncExitStack
from datetime import datetime, timezone

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

_exit_stack = AsyncExitStack()
_checkpointer: AsyncSqliteSaver | None = None

DB_PATH = "data/checkpoints.db"


def _get_meta_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _ensure_meta_table(conn)
    return conn


def _ensure_meta_table(conn: sqlite3.Connection):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS sessions_meta (
            session_id       TEXT PRIMARY KEY,
            last_preview     TEXT NOT NULL,
            message_count    INTEGER NOT NULL DEFAULT 0,
            movies_mentioned TEXT NOT NULL DEFAULT '[]',
            created_at       TEXT NOT NULL,
            updated_at       TEXT NOT NULL
        )"""
    )
    # Migrations for new columns
    cols = [r[1] for r in conn.execute("PRAGMA table_info(sessions_meta)").fetchall()]
    if "movies_mentioned" not in cols:
        conn.execute(
            "ALTER TABLE sessions_meta ADD COLUMN movies_mentioned TEXT NOT NULL DEFAULT '[]'"
        )
    if "first_message" not in cols:
        conn.execute(
            "ALTER TABLE sessions_meta ADD COLUMN first_message TEXT NOT NULL DEFAULT ''"
        )
    conn.commit()


_init_lock = asyncio.Lock()


async def get_checkpointer() -> AsyncSqliteSaver:
    global _checkpointer
    if _checkpointer is not None:
        return _checkpointer

    async with _init_lock:
        if _checkpointer is not None:
            return _checkpointer

        cp = await _exit_stack.enter_async_context(
            AsyncSqliteSaver.from_conn_string(DB_PATH)
        )
        await cp.setup()
        with _get_meta_conn() as conn:
            _ensure_meta_table(conn)
        _checkpointer = cp
        return cp


def upsert_session_meta(
    session_id: str,
    preview: str,
    message_count: int,
    movies: list[dict] | None = None,
    first_message: str = "",
):
    movies_json = json.dumps(movies) if movies else "[]"
    now = datetime.now(timezone.utc).isoformat()
    with _get_meta_conn() as conn:
        conn.execute(
            """INSERT INTO sessions_meta
                 (session_id, last_preview, message_count, movies_mentioned, first_message, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(session_id) DO UPDATE SET
               last_preview = excluded.last_preview,
               message_count = excluded.message_count,
               movies_mentioned = excluded.movies_mentioned,
               updated_at = excluded.updated_at""",
            (session_id, preview, message_count, movies_json, first_message, now, now),
        )
        conn.commit()


def list_sessions_meta(limit: int, offset: int) -> tuple[list[dict], int]:
    with _get_meta_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM sessions_meta").fetchone()[0]
        rows = conn.execute(
            "SELECT * FROM sessions_meta ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
        return ([dict(r) for r in rows], total)


def delete_session_meta(session_id: str):
    with _get_meta_conn() as conn:
        conn.execute("DELETE FROM sessions_meta WHERE session_id = ?", (session_id,))
        conn.commit()
