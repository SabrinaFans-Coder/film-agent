from dataclasses import dataclass
import httpx
from app.config import get_settings


@dataclass
class EnrichedMovie:
    title: str
    year: int | None
    genres: str
    overview: str | None
    tmdb_id: int | None
    imdb_id: str | None


async def enrich_movie(
    title: str,
    year: int | None = None,
    imdb_id: str | None = None,
) -> EnrichedMovie | None:
    """Query TMDB for movie info. Returns None if not found or on transient errors."""
    settings = get_settings()
    params_base = {"api_key": settings.TMDB_API_KEY, "language": "zh-CN"}

    try:
        async with httpx.AsyncClient(
            base_url=settings.TMDB_BASE_URL, timeout=20.0
        ) as client:
            # Prefer imdb_id lookup if available
            if imdb_id:
                resp = await client.get(
                    f"/find/{imdb_id}",
                    params={**params_base, "external_source": "imdb_id"},
                )
                resp.raise_for_status()
                results = resp.json().get("movie_results", [])
                if results:
                    detail = await client.get(
                        f"/movie/{results[0]['id']}", params=params_base
                    )
                    detail.raise_for_status()
                    data = detail.json()
                    return EnrichedMovie(
                        title=data.get("title", title),
                        year=int(data["release_date"][:4]) if data.get("release_date") else year,
                        genres="、".join(g["name"] for g in data.get("genres", [])),
                        overview=data.get("overview"),
                        tmdb_id=data["id"],
                        imdb_id=data.get("imdb_id") or imdb_id,
                    )

            # Fallback: search by title + year
            params = {**params_base, "query": title}
            if year:
                params["year"] = str(year)
            resp = await client.get("/search/movie", params=params)
            resp.raise_for_status()
            results = resp.json().get("results", [])
            if not results:
                return None

            detail = await client.get(
                f"/movie/{results[0]['id']}", params=params_base
            )
            detail.raise_for_status()
            data = detail.json()
            return EnrichedMovie(
                title=data.get("title", title),
                year=int(data["release_date"][:4]) if data.get("release_date") else year,
                genres="、".join(g["name"] for g in data.get("genres", [])),
                overview=data.get("overview"),
                tmdb_id=data["id"],
                imdb_id=data.get("imdb_id") or imdb_id,
            )
    except Exception:
        return None
