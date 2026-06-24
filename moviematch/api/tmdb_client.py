"""Thin wrapper around the TMDB REST API.

Only the handful of endpoints MovieMatch needs are exposed. Network and HTTP
errors are normalised into :class:`TMDBError` so the GUI can show one friendly
message instead of leaking ``requests`` internals.
"""

from __future__ import annotations

import requests

from .. import config
from ..models import Movie


class TMDBError(Exception):
    """Raised for any problem talking to TMDB (network, auth, bad response)."""


class TMDBClient:
    """Stateful client that caches the genre id->name lookup table."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or config.get_api_key()
        if not self.api_key:
            raise TMDBError(
                "No TMDB API key found. Copy .env.example to .env and add your key."
            )
        self._session = requests.Session()
        self._genre_lookup: dict[int, str] | None = None

    # ---- low-level request helper ---------------------------------------
    def _get(self, path: str, **params) -> dict:
        params["api_key"] = self.api_key
        url = f"{config.TMDB_BASE_URL}{path}"
        try:
            resp = self._session.get(url, params=params, timeout=config.REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            raise TMDBError(f"Network error contacting TMDB: {exc}") from exc

        if resp.status_code == 401:
            raise TMDBError("TMDB rejected the API key (401). Check your .env file.")
        if resp.status_code == 404:
            raise TMDBError("Requested resource was not found on TMDB (404).")
        if not resp.ok:
            raise TMDBError(f"TMDB returned HTTP {resp.status_code}.")
        try:
            return resp.json()
        except ValueError as exc:
            raise TMDBError("TMDB returned a malformed response.") from exc

    # ---- genres ----------------------------------------------------------
    def genre_lookup(self) -> dict[int, str]:
        """Return (and cache) the ``{genre_id: name}`` map."""
        if self._genre_lookup is None:
            data = self._get("/genre/movie/list", language="en-US")
            self._genre_lookup = {g["id"]: g["name"] for g in data.get("genres", [])}
        return self._genre_lookup

    # ---- public endpoints -----------------------------------------------
    def search(self, query: str, page: int = 1) -> list[Movie]:
        """Search movies by title."""
        if not query.strip():
            return []
        data = self._get("/search/movie", query=query, page=page, include_adult="false")
        lookup = self.genre_lookup()
        return [Movie.from_tmdb_search(item, lookup) for item in data.get("results", [])]

    def details(self, movie_id: int) -> Movie:
        """Full details for one movie, including keywords (for the recommender)."""
        data = self._get(f"/movie/{movie_id}", append_to_response="keywords")
        return Movie.from_tmdb_details(data)

    def popular(self, page: int = 1) -> list[Movie]:
        """A page of currently popular movies (used to seed recommendations)."""
        return self._movie_list("/movie/popular", page)

    def now_playing(self, page: int = 1) -> list[Movie]:
        """Movies currently in theatres — the 'latest' releases."""
        return self._movie_list("/movie/now_playing", page)

    def top_rated(self, page: int = 1) -> list[Movie]:
        """The highest-rated movies of all time."""
        return self._movie_list("/movie/top_rated", page)

    def upcoming(self, page: int = 1) -> list[Movie]:
        """Movies releasing soon."""
        return self._movie_list("/movie/upcoming", page)

    def _movie_list(self, path: str, page: int) -> list[Movie]:
        """Shared helper for the simple paginated movie-list endpoints."""
        data = self._get(path, page=page)
        lookup = self.genre_lookup()
        return [Movie.from_tmdb_search(item, lookup) for item in data.get("results", [])]

    def discover_by_genres(self, genre_names: list[str], page: int = 1) -> list[Movie]:
        """Discover movies matching any of the given genre names."""
        lookup = self.genre_lookup()
        name_to_id = {name: gid for gid, name in lookup.items()}
        ids = [str(name_to_id[n]) for n in genre_names if n in name_to_id]
        if not ids:
            return []
        data = self._get(
            "/discover/movie",
            with_genres="|".join(ids),     # "|" == OR
            sort_by="popularity.desc",
            page=page,
            include_adult="false",
        )
        return [Movie.from_tmdb_search(item, lookup) for item in data.get("results", [])]
