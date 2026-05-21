from langchain_core.tools import tool
from app.services.movie_store import MovieStore


@tool
async def get_user_ratings_profile(user_id: str = "default") -> str:
    """查询当前用户的评分档案和观影偏好。

    当用户询问以下类型问题时使用此工具：
    - "根据我的评分推荐电影"
    - "我喜歡什麼类型的电影"
    - "分析我的观影偏好"
    - "我评分最高的电影有哪些"
    - "帮我看看我的观影记录"

    Args:
        user_id: 用户ID，默认为 "default"
    """
    store = MovieStore()
    rows, total = store.list_ratings(user_id, limit=500, offset=0)

    if total == 0:
        return "该用户暂无评分记录，建议先导入豆瓣评分数据。"

    # Analyze ratings
    ratings = [float(r["rating"]) for r in rows if r.get("rating")]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0

    # Count genres
    genre_counts = {}
    for r in rows:
        genres_str = r.get("genres") or ""
        for g in genres_str.split("、"):
            g = g.strip()
            if g:
                genre_counts[g] = genre_counts.get(g, 0) + 1

    top_genres = sorted(genre_counts.items(), key=lambda x: -x[1])[:10]

    # Top rated (limit to 10, exclude empty ratings)
    with_rating = [r for r in rows if r.get("rating")]
    with_rating.sort(key=lambda r: -(r["rating"] or 0))
    top_rated = with_rating[:10]

    # By decade
    decade_counts = {}
    for r in rows:
        year = r.get("movie_year") or r.get("year")
        if year:
            decade = (year // 10) * 10
            decade_counts[decade] = decade_counts.get(decade, 0) + 1

    lines = [
        f"用户 {user_id} 的评分档案（共 {total} 部）：",
        f"平均评分：{avg_rating:.1f} / 5",
        "",
        "偏好类型（出现次数）：",
    ]
    for genre, count in top_genres:
        lines.append(f"  - {genre}：{count}")

    if decade_counts:
        lines.append("\n年代分布：")
        for decade in sorted(decade_counts.keys()):
            lines.append(f"  - {decade}年代：{decade_counts[decade]}")

    lines.append("\n评分最高的电影：")
    for i, r in enumerate(top_rated, 1):
        year = r.get("movie_year") or r.get("year", "")
        genres = r.get("genres") or ""
        review = r.get("review")
        line = f"  {i}.《{r['title']}》（{year}）评分：{'★' * int(r['rating'])}{'☆' * (5 - int(r['rating']))}  类型：{genres}"
        if review:
            line += f"  评价：{review}"
        lines.append(line)

    return "\n".join(lines)
