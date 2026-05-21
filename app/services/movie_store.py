from app.db.mysql import get_conn


class MovieStore:
    def find_movie(
        self, imdb_id: str | None, title: str, year: int | None
    ) -> dict | None:
        conn = get_conn()
        cur = conn.cursor(dictionary=True)
        if imdb_id:
            cur.execute("SELECT * FROM movies WHERE imdb_id = %s", (imdb_id,))
            row = cur.fetchone()
            if row:
                conn.close()
                return row
        if year:
            cur.execute(
                "SELECT * FROM movies WHERE title = %s AND year = %s", (title, year)
            )
            row = cur.fetchone()
            if row:
                conn.close()
                return row
        conn.close()
        return None

    def insert_movie(
        self, *,
        imdb_id: str | None = None, title: str = "", year: int | None = None,
        genres: str | None = None, overview: str | None = None,
        tmdb_id: int | None = None, release_date: str | None = None,
    ) -> int:
        conn = get_conn()
        cur = conn.cursor()
        if imdb_id:
            cur.execute("SELECT id FROM movies WHERE imdb_id = %s", (imdb_id,))
            row = cur.fetchone()
            if row:
                conn.close()
                return row[0]
        if tmdb_id:
            cur.execute("SELECT id FROM movies WHERE tmdb_id = %s", (tmdb_id,))
            row = cur.fetchone()
            if row:
                conn.close()
                return row[0]
        cur.execute(
            """INSERT INTO movies (tmdb_id, imdb_id, title, year, genres, overview, release_date)
               VALUES (%s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)""",
            (tmdb_id, imdb_id, title, year, genres, overview, release_date),
        )
        conn.commit()
        mid = cur.lastrowid
        conn.close()
        return mid

    def upsert_rating(
        self, *,
        user_id: str = "", movie_id: int = 0,
        douban_id: str | None = None, imdb_id: str | None = None,
        title: str = "", rating: float | None = None,
        review: str | None = None, tagged_date: str | None = None,
        source_url: str | None = None,
    ):
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO user_ratings
               (user_id, movie_id, douban_id, imdb_id, title, rating, review, tagged_date, source_url)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
               rating = VALUES(rating), review = VALUES(review),
               tagged_date = VALUES(tagged_date), movie_id = VALUES(movie_id)""",
            (user_id, movie_id, douban_id, imdb_id, title, rating, review, tagged_date, source_url),
        )
        conn.commit()
        conn.close()

    def list_ratings(
        self, user_id: str, limit: int = 20, offset: int = 0
    ) -> tuple[list[dict], int]:
        conn = get_conn()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT COUNT(*) as cnt FROM user_ratings WHERE user_id = %s", (user_id,)
        )
        total = cur.fetchone()["cnt"]
        cur.execute(
            """SELECT ur.*, m.genres, m.overview, m.year as movie_year
               FROM user_ratings ur
               LEFT JOIN movies m ON ur.movie_id = m.id
               WHERE ur.user_id = %s
               ORDER BY ur.created_at DESC LIMIT %s OFFSET %s""",
            (user_id, limit, offset),
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows, total

    def update_rating(
        self, user_id: str, imdb_id: str, *, rating: float | None = None, review: str | None = None
    ):
        conn = get_conn()
        cur = conn.cursor()
        parts = []
        vals = []
        if rating is not None:
            parts.append("rating = %s")
            vals.append(rating)
        if review is not None:
            parts.append("review = %s")
            vals.append(review)
        if parts:
            vals.extend([user_id, imdb_id])
            cur.execute(
                f"UPDATE user_ratings SET {', '.join(parts)} WHERE user_id = %s AND imdb_id = %s",
                vals,
            )
        conn.commit()
        conn.close()

    def delete_rating(self, user_id: str, imdb_id: str) -> bool:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM user_ratings WHERE user_id = %s AND imdb_id = %s",
            (user_id, imdb_id),
        )
        deleted = cur.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def list_ratings_with_filter(
        self, user_id: str, limit: int = 20, offset: int = 0,
        min_rating: int | None = None, sort_by: str = "created_at",
        search: str | None = None,
    ) -> tuple[list[dict], int]:
        conn = get_conn()
        cur = conn.cursor(dictionary=True)
        where = "WHERE ur.user_id = %s"
        params: list = [user_id]
        if min_rating is not None:
            where += " AND ur.rating >= %s"
            params.append(min_rating)
        if search:
            where += " AND ur.title LIKE %s"
            params.append(f"%{search}%")
        cur.execute(f"SELECT COUNT(*) as cnt FROM user_ratings ur {where}", params)
        total = cur.fetchone()["cnt"]
        order = "ur.created_at DESC" if sort_by == "created_at" else "ur.rating DESC"
        cur.execute(
            f"""SELECT ur.*, m.genres, m.overview, m.year as movie_year
               FROM user_ratings ur
               LEFT JOIN movies m ON ur.movie_id = m.id
               {where} ORDER BY {order} LIMIT %s OFFSET %s""",
            params + [limit, offset],
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows, total
