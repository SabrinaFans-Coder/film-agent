import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.sync_service import SyncResult, sync_user_ratings

CSV_BYTES = (
    "豆瓣ID,标题,IMDb ID,上映日期,标记日期,我的评分,我的评价,条目链接\n"
    "1,星际穿越,tt0816692,2014/11/7,2026/5/16,5,神作,https://a\n"
    "2,不存在电影,tt99999999,2025/1/1,2026/5/16,3,?,https://b\n"
).encode("utf-8-sig")


@pytest.mark.asyncio
async def test_sync_counts():
    with patch("app.services.sync_service.parse_csv") as mock_parse, \
         patch("app.services.sync_service.MovieStore") as MockStore, \
         patch("app.services.sync_service.enrich_movie") as mock_enrich, \
         patch("app.services.sync_service.get_embeddings") as mock_emb, \
         patch("app.services.sync_service.load_vector_store") as mock_vs:

        from app.services.csv_parser import ParsedRow
        mock_parse.return_value = [
            ParsedRow("1", "星际穿越", "tt0816692", "2014-11-07", 5.0, "神作", "2026-05-16", "https://a", 2014),
            ParsedRow("2", "不存在电影", "tt99999999", "2025-01-01", 3.0, "?", "2026-05-16", "https://b", 2025),
        ]

        store_instance = MockStore.return_value
        store_instance.find_movie.side_effect = [None, None]
        store_instance.insert_movie.side_effect = [1, 2]

        enriched_mock = MagicMock(
            title="星际穿越", year=2014, genres="科幻、冒险",
            overview="人类穿越虫洞...", tmdb_id=157336, imdb_id="tt0816692",
        )
        mock_enrich.side_effect = [enriched_mock, None]

        mock_vs.return_value = None

        result = await sync_user_ratings(CSV_BYTES, "test_user")

        assert result.total == 2
        assert result.new_movies == 2
        assert result.new_ratings == 2
        assert result.tmdb_enriched == 1
        assert result.new_vectors == 0  # no vector store


@pytest.mark.asyncio
async def test_sync_idempotent():
    with patch("app.services.sync_service.parse_csv") as mock_parse, \
         patch("app.services.sync_service.MovieStore") as MockStore, \
         patch("app.services.sync_service.enrich_movie"), \
         patch("app.services.sync_service.get_embeddings"), \
         patch("app.services.sync_service.load_vector_store") as mock_vs:

        from app.services.csv_parser import ParsedRow
        mock_parse.return_value = [
            ParsedRow("1", "星际穿越", "tt0816692", "2014-11-07", 5.0, "神作", "2026-05-16", "", 2014),
            ParsedRow("1", "星际穿越", "tt0816692", "2014-11-07", 5.0, "神作", "2026-05-16", "", 2014),
        ]

        store_instance = MockStore.return_value
        store_instance.find_movie.return_value = {"id": 1, "imdb_id": "tt0816692"}

        mock_vs.return_value = None

        result = await sync_user_ratings(CSV_BYTES, "test_user")
        assert result.total == 2
        assert result.new_movies == 0  # already exists
        assert result.new_vectors == 0
