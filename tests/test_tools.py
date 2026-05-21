import json
import httpx
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.agent.tools import tmdb_search


@pytest.mark.asyncio
async def test_tmdb_search_found():
    # Create mock responses with dummy request to make raise_for_status() work
    search_response = httpx.Response(
        200,
        json={"results": [{"id": 27205, "title": "Inception"}]},
        request=httpx.Request("GET", "https://api.themoviedb.org/3/search/movie"),
    )
    detail_response = httpx.Response(
        200,
        json={
            "id": 27205,
            "title": "Inception",
            "vote_average": 8.8,
            "overview": "A thief who steals corporate secrets...",
            "release_date": "2010-07-16",
            "genres": [{"name": "Action"}, {"name": "Sci-Fi"}],
            "credits": {"cast": [{"name": "Leonardo DiCaprio"}, {"name": "Joseph Gordon-Levitt"}]}
        },
        request=httpx.Request("GET", "https://api.themoviedb.org/3/movie/27205"),
    )

    # Mock settings
    mock_settings = MagicMock()
    mock_settings.TMDB_API_KEY = "test_key"
    mock_settings.TMDB_BASE_URL = "https://api.themoviedb.org/3"

    with patch("app.agent.tools.get_settings", return_value=mock_settings), patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=[search_response, detail_response])
        mock_client_cls.return_value = mock_client

        result = await tmdb_search.ainvoke({"query": "Inception"})
        assert "Inception" in result
        assert "8.8" in result


@pytest.mark.asyncio
async def test_tmdb_search_not_found():
    search_response = httpx.Response(
        200,
        json={"results": []},
        request=httpx.Request("GET", "https://api.themoviedb.org/3/search/movie"),
    )

    # Mock settings
    mock_settings = MagicMock()
    mock_settings.TMDB_API_KEY = "test_key"
    mock_settings.TMDB_BASE_URL = "https://api.themoviedb.org/3"

    with patch("app.agent.tools.get_settings", return_value=mock_settings), patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=search_response)
        mock_client_cls.return_value = mock_client

        result = await tmdb_search.ainvoke({"query": "不存在的电影xyz"})
        assert "未找到" in result
