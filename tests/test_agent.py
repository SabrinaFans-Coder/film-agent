import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
from langchain_core.messages import AIMessage, HumanMessage
from app.agent.core import AgentCore
from app.db.checkpoint import upsert_session_meta, delete_session_meta


def _mock_checkpointer():
    """Create a mock AsyncSqliteSaver."""
    mock_cp = MagicMock()
    mock_cp.aget_tuple = AsyncMock(return_value=None)
    mock_cp.adelete_thread = AsyncMock()
    return mock_cp


@pytest.mark.asyncio
async def test_agent_chat_returns_reply():
    mock_llm = MagicMock()
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={
        "messages": [HumanMessage(content="你好"), AIMessage(content="你好！我是影视助手。")]
    })
    mock_retriever_tool = MagicMock()
    mock_retriever_tool.name = "search_movie_knowledge"

    with patch("app.agent.core.ChatOpenAI", return_value=mock_llm), \
         patch("app.agent.core.create_agent", return_value=mock_agent), \
         patch("app.agent.core.create_movie_retriever_tool", return_value=mock_retriever_tool), \
         patch("app.agent.core.get_checkpointer", AsyncMock(return_value=_mock_checkpointer())):

        core = AgentCore()
        reply, session_id = await core.chat("你好", session_id="test-session")
        assert "你好" in reply or "影视" in reply
        await core.delete_session("test-session")


@pytest.mark.asyncio
async def test_agent_creates_new_session():
    mock_llm = MagicMock()
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={
        "messages": [HumanMessage(content="好的"), AIMessage(content="好的")]
    })
    mock_retriever_tool = MagicMock()
    mock_retriever_tool.name = "search_movie_knowledge"

    with patch("app.agent.core.ChatOpenAI", return_value=mock_llm), \
         patch("app.agent.core.create_agent", return_value=mock_agent), \
         patch("app.agent.core.create_movie_retriever_tool", return_value=mock_retriever_tool), \
         patch("app.agent.core.get_checkpointer", AsyncMock(return_value=_mock_checkpointer())):

        core = AgentCore()
        reply, sid = await core.chat("好的")
        assert sid is not None
        assert len(sid) > 0
        await core.delete_session(sid)


@pytest.mark.asyncio
async def test_agent_includes_retriever_tool_when_available():
    mock_llm = MagicMock()
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={
        "messages": [HumanMessage(content="推荐"), AIMessage(content="推荐几部科幻片给你...")]
    })
    mock_retriever_tool = MagicMock()
    mock_retriever_tool.name = "search_movie_knowledge"

    with patch("app.agent.core.ChatOpenAI", return_value=mock_llm), \
         patch("app.agent.core.create_agent", return_value=mock_agent), \
         patch("app.agent.core.create_movie_retriever_tool", return_value=mock_retriever_tool), \
         patch("app.agent.core.get_checkpointer", AsyncMock(return_value=_mock_checkpointer())):

        core = AgentCore()
        assert mock_retriever_tool in core.tools


@pytest.mark.asyncio
async def test_agent_excludes_retriever_tool_when_unavailable():
    mock_llm = MagicMock()
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={
        "messages": [HumanMessage(content="你好！"), AIMessage(content="你好！")]
    })

    with patch("app.agent.core.ChatOpenAI", return_value=mock_llm), \
         patch("app.agent.core.create_agent", return_value=mock_agent), \
         patch("app.agent.core.create_movie_retriever_tool", return_value=None), \
         patch("app.agent.core.get_checkpointer", AsyncMock(return_value=_mock_checkpointer())):

        core = AgentCore()
        assert len(core.tools) == 2  # tmdb_search + get_user_ratings_profile


@pytest.mark.asyncio
async def test_agent_chat_creates_session_meta_for_new_session():
    mock_llm = MagicMock()
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={
        "messages": [HumanMessage(content="你好"), AIMessage(content="你好！我是影视助手。")]
    })
    mock_retriever_tool = MagicMock()
    mock_retriever_tool.name = "search_movie_knowledge"

    with patch("app.agent.core.ChatOpenAI", return_value=mock_llm), \
         patch("app.agent.core.create_agent", return_value=mock_agent), \
         patch("app.agent.core.create_movie_retriever_tool", return_value=mock_retriever_tool), \
         patch("app.agent.core.get_checkpointer", AsyncMock(return_value=_mock_checkpointer())):

        core = AgentCore()
        reply, sid = await core.chat("你好")

        result = core.list_sessions(limit=10, offset=0)
        assert result.total >= 1
        found = [s for s in result.sessions if s.session_id == sid]
        assert len(found) == 1
        assert found[0].first_message == "你好"
        assert found[0].message_count == 2

        await core.delete_session(sid)


@pytest.mark.asyncio
async def test_agent_chat_updates_existing_session_meta():
    mock_llm = MagicMock()
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={
        "messages": [
            HumanMessage(content="你好"),
            AIMessage(content="你好！"),
            HumanMessage(content="再推荐一部"),
            AIMessage(content="推荐《星际穿越》"),
        ]
    })
    mock_retriever_tool = MagicMock()
    mock_retriever_tool.name = "search_movie_knowledge"

    with patch("app.agent.core.ChatOpenAI", return_value=mock_llm), \
         patch("app.agent.core.create_agent", return_value=mock_agent), \
         patch("app.agent.core.create_movie_retriever_tool", return_value=mock_retriever_tool), \
         patch("app.agent.core.get_checkpointer", AsyncMock(return_value=_mock_checkpointer())):

        core = AgentCore()
        upsert_session_meta("existing-sid", "old preview", 2)

        reply, sid = await core.chat("再推荐一部", session_id="existing-sid")
        assert sid == "existing-sid"

        result = core.list_sessions(limit=10, offset=0)
        found = [s for s in result.sessions if s.session_id == "existing-sid"]
        assert len(found) == 1
        assert found[0].last_preview == "推荐《星际穿越》"
        assert found[0].message_count == 4

        await core.delete_session(sid)


@pytest.mark.asyncio
async def test_agent_chat_unknown_session_id_starts_new():
    mock_llm = MagicMock()
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={
        "messages": [HumanMessage(content="你好"), AIMessage(content="好的")]
    })
    mock_retriever_tool = MagicMock()
    mock_retriever_tool.name = "search_movie_knowledge"

    with patch("app.agent.core.ChatOpenAI", return_value=mock_llm), \
         patch("app.agent.core.create_agent", return_value=mock_agent), \
         patch("app.agent.core.create_movie_retriever_tool", return_value=mock_retriever_tool), \
         patch("app.agent.core.get_checkpointer", AsyncMock(return_value=_mock_checkpointer())):

        core = AgentCore()
        reply, sid = await core.chat("你好", session_id="nonexistent-id")
        assert sid != "nonexistent-id"

        await core.delete_session(sid)


def test_list_sessions():
    upsert_session_meta("ls-1", "预览一", 3)
    upsert_session_meta("ls-2", "预览二", 5)

    mock_llm = MagicMock()
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={
        "messages": [AIMessage(content="test")]
    })
    mock_retriever_tool = MagicMock()
    mock_retriever_tool.name = "search_movie_knowledge"

    with patch("app.agent.core.ChatOpenAI", return_value=mock_llm), \
         patch("app.agent.core.create_agent", return_value=mock_agent), \
         patch("app.agent.core.create_movie_retriever_tool", return_value=mock_retriever_tool), \
         patch("app.agent.core.get_checkpointer", AsyncMock(return_value=_mock_checkpointer())):

        core = AgentCore()
        result = core.list_sessions(limit=10, offset=0)
        assert result.total >= 2
        assert len(result.sessions) >= 2
        assert result.limit == 10
        assert result.offset == 0

    delete_session_meta("ls-1")
    delete_session_meta("ls-2")


@pytest.mark.asyncio
async def test_get_history_nonexistent_raises_404():
    mock_llm = MagicMock()
    mock_agent = MagicMock()
    mock_retriever_tool = MagicMock()
    mock_retriever_tool.name = "search_movie_knowledge"
    mock_cp = _mock_checkpointer()
    mock_cp.aget_tuple = AsyncMock(return_value=None)

    with patch("app.agent.core.ChatOpenAI", return_value=mock_llm), \
         patch("app.agent.core.create_agent", return_value=mock_agent), \
         patch("app.agent.core.create_movie_retriever_tool", return_value=mock_retriever_tool), \
         patch("app.agent.core.get_checkpointer", AsyncMock(return_value=mock_cp)):

        core = AgentCore()
        with pytest.raises(HTTPException) as exc:
            await core.get_history("does-not-exist")
        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_session():
    upsert_session_meta("del-1", "待删除", 2)

    mock_llm = MagicMock()
    mock_agent = MagicMock()
    mock_agent.ainvoke = AsyncMock(return_value={
        "messages": [AIMessage(content="test")]
    })
    mock_retriever_tool = MagicMock()
    mock_retriever_tool.name = "search_movie_knowledge"

    with patch("app.agent.core.ChatOpenAI", return_value=mock_llm), \
         patch("app.agent.core.create_agent", return_value=mock_agent), \
         patch("app.agent.core.create_movie_retriever_tool", return_value=mock_retriever_tool), \
         patch("app.agent.core.get_checkpointer", AsyncMock(return_value=_mock_checkpointer())):

        core = AgentCore()
        result = await core.delete_session("del-1")
        assert result is True

        sessions = core.list_sessions(limit=100, offset=0).sessions
        assert not any(s.session_id == "del-1" for s in sessions)
