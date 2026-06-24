"""Domain model for a movie.

A single :class:`Movie` dataclass is used across the whole app (API results,
storage, recommendations, analytics) so every layer speaks the same language.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class Movie:
    """A movie and the small amount of metadata MovieMatch cares about."""

    id: int
    title: str
    overview: str = ""
    release_date: str = ""            # "YYYY-MM-DD" as returned by TMDB
    poster_path: str | None = None
    vote_average: float = 0.0         # TMDB community score (0-10)
    genres: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)

    # ---- convenience -----------------------------------------------------
    @property
    def year(self) -> int | None:
        """Release year as an int, or ``None`` if unknown."""
        if self.release_date and len(self.release_date) >= 4:
            try:
                return int(self.release_date[:4])
            except ValueError:
                return None
        return None

    @property
    def decade(self) -> str | None:
        """Decade label like ``"1990s"`` for analytics, or ``None``."""
        y = self.year
        return f"{(y // 10) * 10}s" if y is not None else None

    # ---- (de)serialisation for SQLite ------------------------------------
    @classmethod
    def from_tmdb_search(cls, data: dict, genre_lookup: dict[int, str]) -> "Movie":
        """Build a Movie from a TMDB *search* result (genre_ids only)."""
        return cls(
            id=data["id"],
            title=data.get("title", "Untitled"),
            overview=data.get("overview", ""),
            release_date=data.get("release_date", "") or "",
            poster_path=data.get("poster_path"),
            vote_average=float(data.get("vote_average", 0.0) or 0.0),
            genres=[genre_lookup[g] for g in data.get("genre_ids", []) if g in genre_lookup],
        )

    @classmethod
    def from_tmdb_details(cls, data: dict) -> "Movie":
        """Build a Movie from a full TMDB *details* response."""
        keywords = []
        kw_block = data.get("keywords", {})
        for kw in kw_block.get("keywords", []):
            keywords.append(kw["name"])
        return cls(
            id=data["id"],
            title=data.get("title", "Untitled"),
            overview=data.get("overview", ""),
            release_date=data.get("release_date", "") or "",
            poster_path=data.get("poster_path"),
            vote_average=float(data.get("vote_average", 0.0) or 0.0),
            genres=[g["name"] for g in data.get("genres", [])],
            keywords=keywords,
        )

    @classmethod
    def from_row(cls, row) -> "Movie":
        """Rebuild a Movie from a SQLite row (see storage schema)."""
        return cls(
            id=row["movie_id"],
            title=row["title"],
            overview=row["overview"] or "",
            release_date=row["release_date"] or "",
            poster_path=row["poster_path"],
            vote_average=row["vote_average"] or 0.0,
            genres=json.loads(row["genres"] or "[]"),
            keywords=json.loads(row["keywords"] or "[]"),
        )

    def to_storage_dict(self) -> dict:
        """Flatten to primitives for an SQLite ``INSERT``."""
        return {
            "movie_id": self.id,
            "title": self.title,
            "overview": self.overview,
            "release_date": self.release_date,
            "poster_path": self.poster_path,
            "vote_average": self.vote_average,
            "genres": json.dumps(self.genres),
            "keywords": json.dumps(self.keywords),
        }
