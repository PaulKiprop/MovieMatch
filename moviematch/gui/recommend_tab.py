"""Recommendations tab: build a taste profile and surface matching movies."""

from __future__ import annotations

from collections import Counter
from tkinter import ttk

from ..models import Movie
from ..recommender.content_based import Recommendation, recommend
from .components import run_async
from .poster_grid import PosterGrid

# How much each signal contributes to the taste profile.
FAVORITE_WEIGHT = 4.0
RATING_WEIGHTS = {1: -1.0, 2: 0.0, 3: 1.0, 4: 2.5, 5: 4.0}


class RecommendTab(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=10)
        self.app = app
        self._recs: list[Recommendation] = []

        header = ttk.Frame(self)
        header.pack(fill="x")
        ttk.Label(header, text="Recommended for you",
                  font=("Segoe UI", 12, "bold")).pack(side="left")
        self._btn = ttk.Button(header, text="Generate recommendations",
                               command=self.generate)
        self._btn.pack(side="right")

        self._status = ttk.Label(
            self,
            text="Rate or favourite a few movies, then generate recommendations.",
            foreground="#555",
        )
        self._status.pack(anchor="w", pady=(6, 4))

        self._grid = PosterGrid(self, on_open=self.app.open_details,
                                poster_loader=self.app.poster_loader)
        self._grid.pack(fill="both", expand=True)

    # ---- profile ---------------------------------------------------------
    def _gather_liked(self) -> list[tuple[Movie, float]]:
        """Combine favourites and ratings into weighted (movie, weight) pairs."""
        liked: dict[int, tuple[Movie, float]] = {}
        for movie in self.app.storage.list_favorites():
            liked[movie.id] = (movie, FAVORITE_WEIGHT)
        for movie, rating in self.app.storage.list_ratings():
            weight = RATING_WEIGHTS.get(rating, 0.0)
            prev = liked.get(movie.id)
            base = prev[1] if prev else 0.0
            liked[movie.id] = (movie, base + weight)
        # Only keep positive signals — disliked movies shouldn't shape taste.
        return [(m, w) for m, w in liked.values() if w > 0]

    def _candidate_genres(self, liked: list[tuple[Movie, float]]) -> list[str]:
        counts: Counter = Counter()
        for movie, weight in liked:
            for g in movie.genres:
                counts[g] += weight
        return [g for g, _ in counts.most_common(3)]

    # ---- generate --------------------------------------------------------
    def generate(self) -> None:
        liked = self._gather_liked()
        if not liked:
            self._grid.show_message(
                "Nothing to base recommendations on yet — rate or favourite some movies."
            )
            self._status.configure(text="No taste profile yet.")
            return

        self._status.configure(text="Building your taste profile and fetching candidates…")
        self._btn.configure(state="disabled")
        genres = self._candidate_genres(liked)
        exclude = self._seen_ids()

        run_async(
            self,
            lambda: self._fetch_and_rank(liked, genres, exclude),
            self._show,
            self._error,
        )

    def _seen_ids(self) -> set[int]:
        seen = {m.id for m in self.app.storage.list_favorites()}
        seen |= {m.id for m, _ in self.app.storage.list_ratings()}
        return seen

    def _fetch_and_rank(self, liked, genres, exclude) -> list[Recommendation]:
        """Runs in a background thread: gather a candidate pool from TMDB,
        de-duplicate it, then score it with the content-based recommender."""
        pool: dict[int, Movie] = {}
        for page in (1, 2):
            for m in self.app.tmdb.discover_by_genres(genres, page=page):
                pool[m.id] = m
        for m in self.app.tmdb.popular(page=1):     # broaden beyond top genres
            pool.setdefault(m.id, m)
        return recommend(liked, list(pool.values()), exclude_ids=exclude, top_n=25)

    def _show(self, recs: list[Recommendation]) -> None:
        self._btn.configure(state="normal")
        self._recs = recs
        if not recs:
            self._grid.show_message("No fresh recommendations found — try rating more movies.")
            self._status.configure(text="No recommendations.")
            return

        captions = {}
        for rec in recs:
            reasons = ", ".join(rec.reasons) if rec.reasons else "similar taste"
            captions[rec.movie.id] = f"{rec.score * 100:.0f}% match · {reasons}"

        self._grid.set_movies([r.movie for r in recs], captions=captions)
        self._status.configure(text=f"{len(recs)} recommendation(s). Click a poster to open.")

    def _error(self, exc: Exception) -> None:
        self._btn.configure(state="normal")
        self._grid.show_message(f"Error: {exc}")
        self._status.configure(text=f"Error: {exc}")
