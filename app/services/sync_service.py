import asyncio
from dataclasses import dataclass, field
from app.services.csv_parser import parse_csv
from app.services.tmdb_enricher import enrich_movie
from app.services.movie_store import MovieStore
from app.rag.embeddings import get_embeddings
from app.rag.vector_store import load_vector_store


@dataclass
class SyncResult:
    total: int = 0
    new_movies: int = 0
    new_ratings: int = 0
    new_vectors: int = 0
    skipped: int = 0
    tmdb_enriched: int = 0


async def sync_user_ratings(file_content: bytes, user_id: str) -> SyncResult:
    rows = parse_csv(file_content)
    result = SyncResult(total=len(rows))
    store = MovieStore()

    embeddings = get_embeddings()
    vector_store = load_vector_store(embeddings)

    for row in rows:
        await asyncio.sleep(0.05)  # rate-limit TMDB API calls
        # 1. Find or create movie in MySQL
        movie = store.find_movie(
            imdb_id=row.imdb_id, title=row.title, year=row.year
        )
        enriched = None

        if movie:
            movie_id = movie["id"]
        else:
            enriched = await enrich_movie(
                title=row.title, year=row.year, imdb_id=row.imdb_id
            )
            if enriched:
                result.tmdb_enriched += 1
                movie_id = store.insert_movie(
                    imdb_id=enriched.imdb_id,
                    title=enriched.title,
                    year=enriched.year,
                    genres=enriched.genres,
                    overview=enriched.overview,
                    tmdb_id=enriched.tmdb_id,
                )
            else:
                movie_id = store.insert_movie(
                    imdb_id=row.imdb_id,
                    title=row.title,
                    year=row.year,
                )
            result.new_movies += 1

        # 2. Upsert user rating
        store.upsert_rating(
            user_id=user_id,
            movie_id=movie_id,
            douban_id=row.douban_id,
            imdb_id=row.imdb_id,
            title=row.title,
            rating=row.rating,
            review=row.review,
            tagged_date=row.tagged_date,
            source_url=row.source_url,
        )
        result.new_ratings += 1

        # 3. Vector store — only if TMDB found it
        if vector_store and enriched and enriched.imdb_id:
            collection = vector_store._collection
            try:
                existing = collection.get(where={"imdb_id": enriched.imdb_id})
                already_exists = bool(existing.get("ids"))
            except Exception:
                already_exists = False
            if not already_exists:
                embedding_text = (
                    f"标题：{enriched.title}\n"
                    f"类型：{enriched.genres}\n"
                    f"简介：{enriched.overview or ''}"
                )
                embedding_vector = embeddings.embed_query(embedding_text)
                collection.add(
                    embeddings=[embedding_vector],
                    documents=[embedding_text],
                    metadatas=[{
                        "imdb_id": enriched.imdb_id,
                        "title": enriched.title,
                    }],
                    ids=[f"rating_{enriched.imdb_id}"],
                )
                result.new_vectors += 1

    return result
