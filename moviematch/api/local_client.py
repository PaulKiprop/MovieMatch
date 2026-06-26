"""Local (offline) client — mirrors the public interface of TMDBClient.

Reads from ``data_store/movies_offline.json``, a real TMDB snapshot generated
by ``scripts/seed_offline.py``.  Used automatically when no TMDB API key is
configured so the app works for reviewers who clone the project.
"""

from __future__ import annotations

import json
from pathlib import Path

from .. import config
from ..models import Movie

_OFFLINE_JSON = config.PROJECT_ROOT / "data_store" / "movies_offline.json"

# Number of results returned per "page" — matches TMDB's default.
_PAGE_SIZE = 20


class OfflineDataError(Exception):
    """Raised when the offline dataset is missing or unreadable."""


class LocalClient:
    """Read-only client backed by the bundled offline JSON dataset.

    Every method signature matches ``TMDBClient`` exactly so the GUI and
    recommender require no changes when this client is used as a fallback.
    """

    def __init__(self) -> None:
        if not _OFFLINE_JSON.exists():
            raise OfflineDataError(
                f"Offline dataset not found at {_OFFLINE_JSON}.\n"
                "Run  python scripts/seed_offline.py  to generate it."
            )
        raw = json.loads(_OFFLINE_JSON.read_text(encoding="utf-8"))
        self._movies: list[Movie] = [self._from_dict(r) for r in raw]
        # Build a fast id → Movie index.
        self._index: dict[int, Movie] = {m.id: m for m in self._movies}

    # ── internal ────────────────────────────────────────────────────────────

    @staticmethod
    def _from_dict(d: dict) -> Movie:
        return Movie(
            id=d["id"],
            title=d.get("title", "Untitled"),
            overview=d.get("overview", ""),
            release_date=d.get("release_date", "") or "",
            poster_path=d.get("poster_path"),
            vote_average=float(d.get("vote_average", 0.0) or 0.0),
            genres=d.get("genres", []),
            keywords=d.get("keywords", []),
        )

    def _page(self, movies: list[Movie], page: int) -> list[Movie]:
        start = (page - 1) * _PAGE_SIZE
        return movies[start: start + _PAGE_SIZE]

    # ── public API (matches TMDBClient) ─────────────────────────────────────

    def search(self, query: str, page: int = 1) -> list[Movie]:
        """Case-insensitive substring search on title."""
        q = query.strip().lower()
        if not q:
            return []
        matched = [m for m in self._movies if q in m.title.lower()]
        return self._page(matched, page)

    def details(self, movie_id: int) -> Movie:
        """Return the full movie record by id."""
        movie = self._index.get(movie_id)
        if movie is None:
            raise OfflineDataError(f"Movie id {movie_id} not in offline dataset.")
        return movie

    def popular(self, page: int = 1) -> list[Movie]:
        """Highest-rated movies — offline proxy for 'popular'."""
        sorted_movies = sorted(self._movies, key=lambda m: m.vote_average, reverse=True)
        return self._page(sorted_movies, page)

    def now_playing(self, page: int = 1) -> list[Movie]:
        """Movies from the last 3 years — offline proxy for 'now playing'."""
        recent = [m for m in self._movies if (m.year or 0) >= 2021]
        if not recent:
            recent = self._movies          # graceful fallback if dataset is old
        return self._page(recent, page)

    def top_rated(self, page: int = 1) -> list[Movie]:
        """Same as popular() — top-rated by vote_average."""
        return self.popular(page)

    def upcoming(self, page: int = 1) -> list[Movie]:
        """Last page of dataset as a stand-in for 'upcoming'."""
        upcoming = sorted(self._movies, key=lambda m: m.release_date or "", reverse=True)
        return self._page(upcoming, page)

    def discover_by_genres(self, genre_names: list[str], page: int = 1) -> list[Movie]:
        """Filter dataset by genre — used by the recommendation engine."""
        genre_set = {g.lower() for g in genre_names}
        matched = [
            m for m in self._movies
            if any(g.lower() in genre_set for g in m.genres)
        ]
        return self._page(matched, page)
