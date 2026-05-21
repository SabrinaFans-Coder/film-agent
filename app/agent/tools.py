import asyncio
import httpx
from langchain_core.tools import tool
from app.config import get_settings


@tool
async def tmdb_search(query: str) -> str:
    """搜索电影信息。当用户询问具体影片时使用此工具。

    Args:
        query: 电影名称或关键词
    """
    settings = get_settings()
    params = {"api_key": settings.TMDB_API_KEY, "query": query, "language": "zh-CN"}

    try:
        async with httpx.AsyncClient(
            base_url=settings.TMDB_BASE_URL, timeout=15.0
        ) as client:
            search_resp = await client.get("/search/movie", params=params)
            search_resp.raise_for_status()
            results = search_resp.json().get("results", [])

            if not results:
                return f"未找到与「{query}」相关的电影信息。"

            # Fetch basic details for top 3 movies in parallel
            top_n = results[:3]
            basic_params = {"api_key": settings.TMDB_API_KEY, "language": "zh-CN"}

            async def fetch_basic(movie):
                resp = await client.get(f"/movie/{movie['id']}", params=basic_params)
                resp.raise_for_status()
                return resp.json()

            movies_data = []
            gathered = await asyncio.gather(
                *(fetch_basic(m) for m in top_n), return_exceptions=True
            )
            for i, result in enumerate(gathered):
                if isinstance(result, Exception):
                    # Use search result as fallback for failed fetches
                    m = top_n[i]
                    movies_data.append({
                        "title": m.get("title", "未知"),
                        "original_title": m.get("original_title", ""),
                        "release_date": m.get("release_date", "未知"),
                        "vote_average": m.get("vote_average", "未知"),
                        "genres": [],
                        "overview": m.get("overview", "暂无简介"),
                    })
                else:
                    movies_data.append(result)

            # Fetch full credits only for the first result
            first_data = movies_data[0]
            try:
                detail_resp = await client.get(
                    f"/movie/{top_n[0]['id']}",
                    params={
                        **basic_params,
                        "append_to_response": "credits",
                    },
                )
                detail_resp.raise_for_status()
                first_data = detail_resp.json()
            except Exception:
                pass  # keep basic data if credits fail

            movies_data[0] = first_data
    except httpx.ConnectTimeout:
        return f"抱歉，无法连接到电影数据库，请稍后再试。"
    except httpx.HTTPStatusError as e:
        return f"查询电影信息时出错（状态码：{e.response.status_code}），请稍后再试。"
    except Exception:
        return f"查询电影信息时出现异常，请稍后再试。"

    # Format all results
    lines = []
    for i, data in enumerate(movies_data):
        genres = "、".join(g["name"] for g in data.get("genres", []))
        lines.append(
            f"--- 结果 {i + 1} ---\n"
            f"片名：{data.get('title', '未知')}\n"
            f"原名：{data.get('original_title', '未知')}\n"
            f"上映日期：{data.get('release_date', '未知')}\n"
            f"评分：{data.get('vote_average', '未知')}\n"
            f"类型：{genres}"
        )
        if i == 0:
            cast = "、".join(
                c["name"] for c in data.get("credits", {}).get("cast", [])[:5]
            )
            lines.append(f"主演：{cast}")
            lines.append(f"简介：{data.get('overview', '暂无简介')}")

    return "\n".join(lines)
