import os
from mysql.connector.pooling import MySQLConnectionPool

_POOL = None

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", "123456"),
    "database": os.getenv("MYSQL_DATABASE", "film_agent"),
    "charset": "utf8mb4",
    "use_pure": True,
    "autocommit": False,
}


def get_conn():
    global _POOL
    if _POOL is None:
        _POOL = MySQLConnectionPool(
            pool_name="film_agent",
            pool_size=5,
            **DB_CONFIG,
        )
    return _POOL.get_connection()


def ensure_schema():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS movies (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            tmdb_id      INT UNIQUE,
            imdb_id      VARCHAR(20) UNIQUE,
            title        VARCHAR(255) NOT NULL,
            year         INT,
            genres       VARCHAR(500),
            overview     TEXT,
            release_date VARCHAR(30),
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
    )
    cur.execute(
        """CREATE TABLE IF NOT EXISTS user_ratings (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            user_id      VARCHAR(50) NOT NULL,
            movie_id     INT,
            douban_id    VARCHAR(30),
            imdb_id      VARCHAR(20),
            title        VARCHAR(255) NOT NULL,
            rating       DECIMAL(3,1),
            review       TEXT,
            tagged_date  VARCHAR(30),
            source_url   VARCHAR(500),
            created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_user_imdb (user_id, imdb_id),
            FOREIGN KEY (movie_id) REFERENCES movies(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""
    )
    conn.commit()
    conn.close()
