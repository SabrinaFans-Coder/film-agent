"""离线索引构建脚本。

用法: python scripts/build_index.py

从 TMDB 按分类拉取电影 → 去重 → 生成 Document → 向量化存入 ChromaDB。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx
from langchain_core.documents import Document
from langchain_chroma import Chroma
from app.config import get_settings
from app.rag.embeddings import get_embeddings


def build_genre_map(genres: list[dict]) -> dict[int, str]:
    """将 TMDB genre 列表转为 {id: name} 映射。"""
    return {g["id"]: g["name"] for g in genres}


def deduplicate_movies(movies: list[dict]) -> list[dict]:
    """按 movie_id 去重，保持首次出现顺序。"""
    seen: set[int] = set()
    unique = []
    for m in movies:
        mid = m["id"]
        if mid not in seen:
            seen.add(mid)
            unique.append(m)
    return unique


def format_movie_document(movie: dict, genre_map: dict[int, str]) -> Document:
    """将单条 TMDB 电影数据转为 LangChain Document。"""
    genre_ids = movie.get("genre_ids", [])
    genre_names = "、".join(genre_map.get(gid, "未知") for gid in genre_ids)

    content = (
        f"片名：{movie.get('title', '未知')}\n"
        f"简介：{movie.get('overview', '暂无简介')}\n"
        f"类型：{genre_names}\n"
        f"上映日期：{movie.get('release_date', '未知')}\n"
        f"评分：{movie.get('vote_average', '未知')}"
    )

    return Document(
        page_content=content,
        metadata={
            "movie_id": movie["id"],
            "title": movie.get("title", ""),
            "release_date": movie.get("release_date", ""),
        },
    )


async def main():
    settings = get_settings()
    params_base = {"api_key": settings.TMDB_API_KEY, "language": "zh-CN"}

    async with httpx.AsyncClient(
        base_url=settings.TMDB_BASE_URL, timeout=30.0
    ) as client:
        # 1. Build genre map
        genre_resp = await client.get("/genre/movie/list", params=params_base)
        genre_resp.raise_for_status()
        genre_map = build_genre_map(genre_resp.json()["genres"])
        print(f"获取到 {len(genre_map)} 个电影分类")

        # 2. Fetch movies per genre (TOP 60 each)
        all_movies: list[dict] = []
        for genre_id in genre_map:
            for page in range(1, 4):
                resp = await client.get(
                    "/discover/movie",
                    params={
                        **params_base,
                        "with_genres": genre_id,
                        "sort_by": "popularity.desc",
                        "page": page,
                    },
                )
                resp.raise_for_status()
                page_movies = resp.json().get("results", [])
                all_movies.extend(page_movies)
                if not page_movies:
                    break

        print(f"共拉取 {len(all_movies)} 条电影数据（含重复）")

        # 3. Deduplicate
        unique_movies = deduplicate_movies(all_movies)
        print(f"去重后剩余 {len(unique_movies)} 部电影")

        # 4. Create documents
        docs = [format_movie_document(m, genre_map) for m in unique_movies]

    # 5. Embed and persist
    print("正在生成向量索引（首次运行需下载 embedding 模型）...")
    embeddings = get_embeddings()
    Chroma.from_documents(docs, embeddings, persist_directory="data/chroma")
    print(f"索引构建完成！{len(docs)} 部电影已存入 data/chroma/")


if __name__ == "__main__":
    asyncio.run(main())
