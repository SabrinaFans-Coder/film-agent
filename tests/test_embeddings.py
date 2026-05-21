import pytest
from app.rag.embeddings import get_embeddings


def test_get_embeddings_returns_huggingface_embeddings():
    model = get_embeddings()
    assert model.model_name == "BAAI/bge-small-zh-v1.5"
    assert model.model_kwargs == {"device": "cpu"}
    assert model.encode_kwargs == {"normalize_embeddings": True}
