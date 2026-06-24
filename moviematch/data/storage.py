"""Local persistence using SQLite (standard library, no external deps).

Three concerns are stored:
  * ``movies``     - a cache of metadata so favourites/ratings survive offline
  * ``favorites``  - which movies the user saved
  * ``ratings``    - the user's 1-5 star ratings
  * ``history``    - a log of viewed movies (powers the analytics tab)

All movie-specific tables reference ``movies(movie_id)`` so we never duplicate
title/genre data.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from .. import config
from ..models import Movie


class Storage:
    """A small data-access layer wrapping a single SQLite connection."""

    def __init__(self, db_path=None):
        config.ensure_data_dir()
        self._conn = sqlite3.connect(str(db_path or config.DB_PATH))
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._create_schema()

    # ---- schema ----------------------------------------------------------
    def _create_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS movies (
                movie_id     INTEGER PRIMARY KEY,
                title        TEXT NOT NULL,
                overview     TEXT,
                release_date TEXT,
                poster_path  TEXT,
                vote_average REAL,
                genres       TEXT,   -- JSON array
                keywords     TEXT    -- JSON array
            );

            CREATE TABLE IF NOT EXISTS favorites (
                movie_id INTEGER PRIMARY KEY REFERENCES movies(movie_id),
                added_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ratings (
                movie_id INTEGER PRIMARY KEY REFERENCES movies(movie_id),
                rating   INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                rated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS history (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                movie_id  INTEGER NOT NULL REFERENCES movies(movie_id),
                viewed_at TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    # ---- movie cache -----------------------------------------------------
    def upsert_movie(self, movie: Movie) -> None:
        """Insert or update the cached metadata for a movie."""
        d = movie.to_storage_dict()
        self._conn.execute(
            """
            INSERT INTO movies (movie_id, title, overview, release_date,
                                poster_path, vote_average, genres, keywords)
            VALUES (:movie_id, :title, :overview, :release_date,
                    :poster_path, :vote_average, :genres, :keywords)
            ON CONFLICT(movie_id) DO UPDATE SET
                title=excluded.title,
                overview=excluded.overview,
                release_date=excluded.release_date,
                poster_path=excluded.poster_path,
                vote_average=excluded.vote_average,
                genres=excluded.genres,
                keywords=excluded.keywords
            """,
            d,
        )
        self._conn.commit()

    def get_movie(self, movie_id: int) -> Movie | None:
        row = self._conn.execute(
            "SELECT * FROM movies WHERE movie_id = ?", (movie_id,)
        ).fetchone()
        return Movie.from_row(row) if row else None

    # ---- favorites -------------------------------------------------------
    def add_favorite(self, movie: Movie) -> None:
        self.upsert_movie(movie)
        self._conn.execute(
            "INSERT OR IGNORE INTO favorites (movie_id, added_at) VALUES (?, ?)",
            (movie.id, self._now()),
        )
        self._conn.commit()

    def remove_favorite(self, movie_id: int) -> None:
        self._conn.execute("DELETE FROM favorites WHERE movie_id = ?", (movie_id,))
        self._conn.commit()

    def is_favorite(self, movie_id: int) -> bool:
        return (
            self._conn.execute(
                "SELECT 1 FROM favorites WHERE movie_id = ?", (movie_id,)
            ).fetchone()
            is not None
        )

    def list_favorites(self) -> list[Movie]:
        rows = self._conn.execute(
            """
            SELECT m.* FROM movies m
            JOIN favorites f ON f.movie_id = m.movie_id
            ORDER BY f.added_at DESC
            """
        ).fetchall()
        return [Movie.from_row(r) for r in rows]

    # ---- ratings ---------------------------------------------------------
    def set_rating(self, movie: Movie, rating: int) -> None:
        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5.")
        self.upsert_movie(movie)
        self._conn.execute(
            """
            INSERT INTO ratings (movie_id, rating, rated_at) VALUES (?, ?, ?)
            ON CONFLICT(movie_id) DO UPDATE SET
                rating=excluded.rating, rated_at=excluded.rated_at
            """,
            (movie.id, rating, self._now()),
        )
        self._conn.commit()

    def get_rating(self, movie_id: int) -> int | None:
        row = self._conn.execute(
            "SELECT rating FROM ratings WHERE movie_id = ?", (movie_id,)
        ).fetchone()
        return row["rating"] if row else None

    def list_ratings(self) -> list[tuple[Movie, int]]:
        rows = self._conn.execute(
            """
            SELECT m.*, r.rating AS user_rating FROM movies m
            JOIN ratings r ON r.movie_id = m.movie_id
            ORDER BY r.rated_at DESC
            """
        ).fetchall()
        return [(Movie.from_row(r), r["user_rating"]) for r in rows]

    # ---- history ---------------------------------------------------------
    def log_view(self, movie: Movie) -> None:
        self.upsert_movie(movie)
        self._conn.execute(
            "INSERT INTO history (movie_id, viewed_at) VALUES (?, ?)",
            (movie.id, self._now()),
        )
        self._conn.commit()

    def list_history(self) -> list[tuple[Movie, str]]:
        rows = self._conn.execute(
            """
            SELECT m.*, h.viewed_at FROM history h
            JOIN movies m ON m.movie_id = h.movie_id
            ORDER BY h.viewed_at DESC
            """
        ).fetchall()
        return [(Movie.from_row(r), r["viewed_at"]) for r in rows]

    def close(self) -> None:
        self._conn.close()
