import os
import pytest

# Force test database before any imports
os.environ["MYSQL_DATABASE"] = "film_agent_test"

from app.db.mysql import get_conn, ensure_schema
from app.services.movie_store import MovieStore


@pytest.fixture(autouse=True)
def _setup_schema():
    ensure_schema()
    yield


def test_ensure_schema_creates_tables():
    ensure_schema()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SHOW TABLES")
    tables = [r[0] for r in cur.fetchall()]
    assert "movies" in tables
    assert "user_ratings" in tables
    conn.close()


def test_get_conn_returns_usable_connection():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT 1")
    assert cur.fetchone() == (1,)
    conn.close()


def test_movies_insert_and_find():
    ensure_schema()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM user_ratings WHERE user_id='test_movies_insert'")
    cur.execute("DELETE FROM movies WHERE imdb_id='tt_test_movies'")
    conn.commit()

    # Insert movie
    cur.execute(
        """INSERT INTO movies (imdb_id, title, year, genres)
           VALUES (%s, %s, %s, %s)
           ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id)""",
        ("tt_test_movies", "测试电影", 2025, "动作"),
    )
    conn.commit()
    mid = cur.lastrowid
    assert mid > 0

    # Find by imdb_id
    cur.execute("SELECT * FROM movies WHERE imdb_id = %s", ("tt_test_movies",))
    row = cur.fetchone()
    assert row is not None
    assert row[3] == "测试电影"  # title column

    # Cleanup
    cur.execute("DELETE FROM movies WHERE imdb_id='tt_test_movies'")
    conn.commit()
    conn.close()


def test_find_and_insert_movie():
    store = MovieStore()
    movie = store.find_movie(imdb_id="tt99999", title="测试电影", year=2025)
    assert movie is None

    mid = store.insert_movie(
        imdb_id="tt99999", title="测试电影", year=2025,
        genres="动作、科幻", overview="一部测试电影", tmdb_id=12345,
    )
    assert mid > 0

    movie = store.find_movie(imdb_id="tt99999", title="测试电影", year=2025)
    assert movie is not None
    assert movie["imdb_id"] == "tt99999"

    # Cleanup
    conn = get_conn()
    conn.cursor().execute("DELETE FROM movies WHERE imdb_id='tt99999'")
    conn.commit()
    conn.close()


def test_upsert_rating_idempotent():
    store = MovieStore()
    mid = store.insert_movie(
        imdb_id="tt88888", title="幂等测试", year=2025,
        genres="动作", overview="测试幂等", tmdb_id=99999,
    )

    store.upsert_rating(
        user_id="test_user", movie_id=mid, douban_id="d1",
        imdb_id="tt88888", title="幂等测试", rating=4.0,
        review="好看", tagged_date="2025-01-01",
    )

    # Second upsert — same user + imdb_id, should update
    store.upsert_rating(
        user_id="test_user", movie_id=mid, douban_id="d1",
        imdb_id="tt88888", title="幂等测试", rating=5.0,
        review="更新评价", tagged_date="2025-01-01",
    )

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT rating, review FROM user_ratings WHERE user_id='test_user' AND imdb_id='tt88888'"
    )
    row = cur.fetchone()
    assert row[0] == 5.0
    assert row[1] == "更新评价"
    cur.execute("SELECT COUNT(*) FROM user_ratings WHERE user_id='test_user'")
    assert cur.fetchone()[0] == 1

    cur.execute("DELETE FROM user_ratings WHERE user_id='test_user' AND imdb_id='tt88888'")
    cur.execute("DELETE FROM movies WHERE imdb_id='tt88888'")
    conn.commit()
    conn.close()
