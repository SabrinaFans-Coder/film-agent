import asyncio
import tempfile
from contextlib import AsyncExitStack
from pathlib import Path

import pytest

import app.db.checkpoint as cp_module


@pytest.fixture(autouse=True)
def clean_checkpoint(monkeypatch):
    """Run each test with a fresh temporary database and reset singleton."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
        db_path = str(Path(tmpdir) / "checkpoints.db")
        monkeypatch.setattr(cp_module, "DB_PATH", db_path)
        monkeypatch.setattr(cp_module, "_checkpointer", None)
        monkeypatch.setattr(cp_module, "_exit_stack", AsyncExitStack())
        yield
        asyncio.run(cp_module._exit_stack.aclose())


from app.db.checkpoint import (
    get_checkpointer,
    upsert_session_meta,
    list_sessions_meta,
    delete_session_meta,
)


def test_get_checkpointer_returns_sqlite_saver():
    cp = asyncio.run(get_checkpointer())
    assert cp is not None
    assert asyncio.run(get_checkpointer()) is cp


def test_upsert_and_list_sessions_meta():
    upsert_session_meta("s1", "这是预览内容", 5)
    upsert_session_meta("s2", "另一条预览", 3)

    sessions, total = list_sessions_meta(limit=10, offset=0)
    assert total == 2
    assert len(sessions) == 2
    assert sessions[0]["session_id"] == "s2"
    assert sessions[0]["last_preview"] == "另一条预览"
    assert sessions[0]["message_count"] == 3
    assert "created_at" in sessions[0]
    assert "updated_at" in sessions[0]


def test_list_sessions_meta_pagination():
    for i in range(5):
        upsert_session_meta(f"s{i}", f"preview {i}", i)

    sessions, total = list_sessions_meta(limit=2, offset=0)
    assert total == 5
    assert len(sessions) == 2

    sessions, total = list_sessions_meta(limit=2, offset=4)
    assert len(sessions) == 1


def test_upsert_session_meta_update():
    upsert_session_meta("s1", "first preview", 3)
    upsert_session_meta("s1", "updated preview", 5)

    sessions, total = list_sessions_meta(limit=10, offset=0)
    assert total == 1
    assert sessions[0]["last_preview"] == "updated preview"
    assert sessions[0]["message_count"] == 5


def test_delete_session_meta():
    upsert_session_meta("to_delete", "preview", 1)
    delete_session_meta("to_delete")

    sessions, total = list_sessions_meta(limit=10, offset=0)
    assert total == 0


def test_delete_session_meta_nonexistent():
    delete_session_meta("does_not_exist")
