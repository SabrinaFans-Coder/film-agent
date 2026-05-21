import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import AsyncClient, ASGITransport

# First, mock the AgentCore before any imports
with patch("app.api.routes.AgentCore") as mock_agent_core_class:
    mock_core = MagicMock()
    mock_core.chat = AsyncMock(return_value=("你好！我是影视助手。", "test-session-1"))
    mock_agent_core_class.return_value = mock_core

    from app.main import app


@pytest.mark.asyncio
async def test_chat_endpoint():
    with patch("app.api.routes.agent_core") as mock_core:
        mock_core.chat = AsyncMock(return_value=("你好！我是影视助手。", "test-session-1"))

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            resp = await client.post("/chat", json={"message": "你好"})
            assert resp.status_code == 200
            data = resp.json()
            assert "reply" in data
            assert "session_id" in data


@pytest.mark.asyncio
async def test_chat_endpoint_empty_message():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        resp = await client.post("/chat", json={"message": ""})
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_chat_endpoint_with_session():
    with patch("app.api.routes.agent_core") as mock_core:
        mock_core.chat = AsyncMock(return_value=("好的", "existing-session"))
        mock_core.sessions = {"existing-session": []}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            resp = await client.post(
                "/chat",
                json={"message": "继续聊", "session_id": "existing-session"},
            )
            assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_sessions_endpoint():
    mock_core = MagicMock()
    mock_result = MagicMock()
    mock_result.model_dump.return_value = {
        "sessions": [], "total": 0, "limit": 20, "offset": 0,
    }
    mock_core.list_sessions.return_value = mock_result

    with patch("app.api.routes.agent_core", mock_core):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/sessions")
            assert resp.status_code == 200
            data = resp.json()
            assert "sessions" in data
            assert "total" in data


@pytest.mark.asyncio
async def test_list_sessions_with_pagination():
    mock_core = MagicMock()
    mock_result = MagicMock()
    mock_result.model_dump.return_value = {
        "sessions": [], "total": 0, "limit": 10, "offset": 5,
    }
    mock_core.list_sessions.return_value = mock_result

    with patch("app.api.routes.agent_core", mock_core):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/sessions?limit=10&offset=5")
            assert resp.status_code == 200
            mock_core.list_sessions.assert_called_once_with(limit=10, offset=5)


@pytest.mark.asyncio
async def test_get_session_messages():
    from app.models.schemas import HistoryResponse
    mock_core = MagicMock()
    mock_core.get_history = AsyncMock(return_value=HistoryResponse(
        session_id="abc", messages=[]
    ))

    with patch("app.api.routes.agent_core", mock_core):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/sessions/abc/messages")
            assert resp.status_code == 200
            data = resp.json()
            assert data["session_id"] == "abc"


@pytest.mark.asyncio
async def test_get_session_messages_not_found():
    from fastapi import HTTPException
    mock_core = MagicMock()
    mock_core.get_history = AsyncMock(side_effect=HTTPException(status_code=404, detail="not found"))

    with patch("app.api.routes.agent_core", mock_core):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/sessions/nonexistent/messages")
            assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_session():
    mock_core = MagicMock()
    mock_core.delete_session = AsyncMock(return_value=True)

    with patch("app.api.routes.agent_core", mock_core):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.delete("/sessions/abc")
            assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_session_not_found():
    from fastapi import HTTPException
    mock_core = MagicMock()
    mock_core.delete_session = AsyncMock(side_effect=HTTPException(status_code=404, detail="not found"))

    with patch("app.api.routes.agent_core", mock_core):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.delete("/sessions/nonexistent")
            assert resp.status_code == 404
