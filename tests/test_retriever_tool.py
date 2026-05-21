import pytest
from unittest.mock import MagicMock, patch
from app.rag.retriever_tool import create_movie_retriever_tool


def test_returns_none_when_no_index():
    with patch("app.rag.retriever_tool.get_embeddings"), \
         patch("app.rag.retriever_tool.load_vector_store", return_value=None):
        result = create_movie_retriever_tool()
        assert result is None


def test_returns_tool_when_index_exists():
    mock_store = MagicMock()
    mock_retriever = MagicMock()
    mock_store.as_retriever.return_value = mock_retriever

    with patch("app.rag.retriever_tool.get_embeddings"), \
         patch("app.rag.retriever_tool.load_vector_store", return_value=mock_store), \
         patch("app.rag.retriever_tool.create_retriever_tool") as mock_create_tool:

        mock_tool = MagicMock()
        mock_create_tool.return_value = mock_tool

        result = create_movie_retriever_tool()
        assert result is mock_tool

    mock_store.as_retriever.assert_called_once_with(search_kwargs={"k": 5})
    mock_create_tool.assert_called_once()
    call_args = mock_create_tool.call_args
    assert call_args[0][0] is mock_retriever
    assert call_args[1]["name"] == "search_movie_knowledge"
