import pytest
from pydantic import ValidationError
from app.models.schemas import ChatRequest, ChatResponse


def test_chat_request_valid():
    req = ChatRequest(message="盗梦空间好看吗")
    assert req.message == "盗梦空间好看吗"
    assert req.session_id is None


def test_chat_request_with_session():
    req = ChatRequest(message="hello", session_id="abc-123")
    assert req.session_id == "abc-123"


def test_chat_request_empty_message_raises():
    with pytest.raises(ValidationError):
        ChatRequest(message="")


def test_chat_response():
    resp = ChatResponse(reply="好的！", session_id="abc-123")
    assert resp.reply == "好的！"
    assert resp.session_id == "abc-123"


from app.models.schemas import HistoryMessage, SessionInfo, SessionListResponse, HistoryResponse


def test_history_message():
    msg = HistoryMessage(role="user", content="你好", timestamp="2026-05-19T10:00:00+00:00")
    assert msg.role == "user"
    assert msg.content == "你好"
    assert msg.timestamp == "2026-05-19T10:00:00+00:00"


def test_session_info():
    info = SessionInfo(
        session_id="abc-123",
        last_preview="这是一条助手的回复内容的前五十个字符...",
        message_count=10,
        created_at="2026-05-19T10:00:00+00:00",
        updated_at="2026-05-19T11:00:00+00:00",
    )
    assert info.session_id == "abc-123"
    assert info.message_count == 10


def test_session_list_response():
    resp = SessionListResponse(
        sessions=[
            SessionInfo(
                session_id="s1",
                last_preview="预览1",
                message_count=3,
                created_at="2026-01-01T00:00:00+00:00",
                updated_at="2026-01-01T00:00:00+00:00",
            )
        ],
        total=1,
        limit=20,
        offset=0,
    )
    assert resp.total == 1
    assert resp.limit == 20
    assert len(resp.sessions) == 1


def test_history_response():
    resp = HistoryResponse(
        session_id="abc-123",
        messages=[
            HistoryMessage(role="user", content="你好", timestamp="2026-05-19T10:00:00+00:00"),
            HistoryMessage(role="assistant", content="你好！有什么可以帮你的？", timestamp="2026-05-19T10:00:01+00:00"),
        ],
    )
    assert resp.session_id == "abc-123"
    assert len(resp.messages) == 2