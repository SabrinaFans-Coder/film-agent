import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import AIMessage, HumanMessage
from app.agent.core import AgentCore


def _make_checkpoint_mock(messages):
    """Create a mock checkpointer that returns the given messages."""
    cp = MagicMock()
    cp.aget_tuple = AsyncMock(return_value=MagicMock(
        checkpoint={"channel_values": {"messages": messages}},
    ))
    return cp


@pytest.mark.asyncio
async def test_stream_chat_yields_tokens():
    mock_llm = MagicMock()
    mock_agent = MagicMock()

    async def mock_astream(input, config=None, stream_mode=None, version=None):
        yield AIMessage(content="你好")
        yield AIMessage(content="你好！我是")
        yield AIMessage(content="你好！我是影视助手。")

    mock_agent.astream = mock_astream
    mock_retriever_tool = MagicMock()
    mock_retriever_tool.name = "search_movie_knowledge"

    messages = [
        HumanMessage(content="你好"),
        AIMessage(content="你好！我是影视助手。"),
    ]

    with patch("app.agent.core.ChatOpenAI", return_value=mock_llm), \
         patch("app.agent.core.create_agent", return_value=mock_agent), \
         patch("app.agent.core.create_movie_retriever_tool", return_value=mock_retriever_tool), \
         patch("app.agent.core.get_checkpointer", AsyncMock(return_value=_make_checkpoint_mock(messages))):

        core = AgentCore()
        chunks = []
        async for chunk in core.stream_chat("你好", "test-session"):
            chunks.append(chunk)

    tokens = [c["content"] for c in chunks if c["type"] == "token"]
    combined = "".join(tokens)
    assert "你好" in combined
    assert "影视助手" in combined
    assert chunks[-1]["type"] == "done"
    assert chunks[-1]["reply"] == combined


@pytest.mark.asyncio
async def test_stream_chat_handles_empty_response():
    mock_llm = MagicMock()
    mock_agent = MagicMock()

    async def mock_astream(input, config=None, stream_mode=None, version=None):
        yield AIMessage(content="")

    mock_agent.astream = mock_astream
    mock_retriever_tool = MagicMock()
    mock_retriever_tool.name = "search_movie_knowledge"

    with patch("app.agent.core.ChatOpenAI", return_value=mock_llm), \
         patch("app.agent.core.create_agent", return_value=mock_agent), \
         patch("app.agent.core.create_movie_retriever_tool", return_value=mock_retriever_tool), \
         patch("app.agent.core.get_checkpointer", AsyncMock(return_value=_make_checkpoint_mock([]))):

        core = AgentCore()
        chunks = [c async for c in core.stream_chat("test", "test-session")]
        assert chunks[-1]["type"] == "done"
