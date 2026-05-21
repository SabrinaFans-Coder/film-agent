import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from app.rag.vector_store import load_vector_store


def test_load_vector_store_missing_dir():
    result = load_vector_store(
        embeddings=MagicMock(),
        persist_dir="nonexistent/path/12345"
    )
    assert result is None


def test_load_vector_store_empty_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        result = load_vector_store(
            embeddings=MagicMock(),
            persist_dir=tmpdir
        )
        assert result is None


def test_load_vector_store_with_index():
    with (
        tempfile.TemporaryDirectory() as tmpdir,
        patch("app.rag.vector_store.Chroma") as mock_chroma,
    ):
        Path(tmpdir).joinpath("chroma.sqlite3").touch()

        mock_embeddings = MagicMock()
        result = load_vector_store(
            embeddings=mock_embeddings,
            persist_dir=tmpdir,
        )

        assert result is not None
        mock_chroma.assert_called_once_with(
            persist_directory=str(tmpdir),
            embedding_function=mock_embeddings,
        )
