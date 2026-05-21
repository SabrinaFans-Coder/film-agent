import pytest
from langchain_core.documents import Document
from scripts.build_index import build_genre_map, deduplicate_movies, format_movie_document


def test_build_genre_map():
    genres = [
        {"id": 28, "name": "动作"},
        {"id": 12, "name": "冒险"},
        {"id": 35, "name": "喜剧"},
    ]
    result = build_genre_map(genres)
    assert result == {28: "动作", 12: "冒险", 35: "喜剧"}


def test_deduplicate_movies():
    movies = [
        {"id": 1, "title": "Movie A"},
        {"id": 2, "title": "Movie B"},
        {"id": 1, "title": "Movie A"},  # duplicate
        {"id": 3, "title": "Movie C"},
    ]
    result = deduplicate_movies(movies)
    assert len(result) == 3
    ids = [m["id"] for m in result]
    assert ids == [1, 2, 3]


def test_deduplicate_movies_empty():
    assert deduplicate_movies([]) == []


def test_format_movie_document():
    movie = {
        "id": 27205,
        "title": "盗梦空间",
        "overview": "一部关于梦境的科幻片",
        "genre_ids": [28, 878],
        "release_date": "2010-07-16",
        "vote_average": 8.8,
    }
    genre_map = {28: "动作", 878: "科幻"}
    doc = format_movie_document(movie, genre_map)
    assert isinstance(doc, Document)
    assert doc.metadata["movie_id"] == 27205
    assert doc.metadata["title"] == "盗梦空间"
    assert doc.metadata["release_date"] == "2010-07-16"
    assert "盗梦空间" in doc.page_content
    assert "动作" in doc.page_content
    assert "科幻" in doc.page_content
    assert "8.8" in doc.page_content
    assert "2010-07-16" in doc.page_content


def test_format_movie_document_missing_fields():
    movie = {"id": 99}
    genre_map = {}
    doc = format_movie_document(movie, genre_map)
    assert "未知" in doc.page_content  # title fallback
    assert "暂无简介" in doc.page_content  # overview fallback
