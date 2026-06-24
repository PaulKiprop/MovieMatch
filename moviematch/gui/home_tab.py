"""Home / landing tab.

Loads a curated list of movies as soon as the app opens, so the user has
something to browse and discover straight away — without having to search
first. A category selector switches between the latest releases, popular,
top-rated and upcoming titles.
"""

from __future__ import annotations

from tkinter import ttk

from ..models import Movie
from .components import run_async
from .poster_grid import PosterGrid

# Label -> the TMDBClient method name that fetches that category.
CATEGORIES = {
    "Now Playing (latest)": "now_playing",
    "Popular": "popular",
    "Top Rated": "top_rated",
    "Upcoming": "upcoming",
}


class HomeTab(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=10)
        self.app = app

        header = ttk.Frame(self)
        header.pack(fill="x")
        ttk.Label(header, text="Discover movies",
                  font=("Segoe UI", 12, "bold")).pack(side="left")

        ttk.Label(header, text="Show:").pack(side="left", padx=(16, 4))
        self._category = ttk.Combobox(
            header, values=list(CATEGORIES), state="readonly", width=22
        )
        self._category.current(0)
        self._category.pack(side="left")
        self._category.bind("<<ComboboxSelected>>", lambda _e: self.load())

        self._btn = ttk.Button(header, text="Refresh", command=self.load)
        self._btn.pack(side="right")

        self._status = ttk.Label(self, text="", foreground="#555")
        self._status.pack(anchor="w", pady=(6, 4))

        self._grid = PosterGrid(self, on_open=self.app.open_details,
                                poster_loader=self.app.poster_loader)
        self._grid.pack(fill="both", expand=True)

    def load(self) -> None:
        """Fetch the selected category in the background."""
        label = self._category.get()
        method_name = CATEGORIES[label]
        self._status.configure(text=f"Loading {label.lower()}…")
        self._btn.configure(state="disabled")

        run_async(
            self,
            lambda: getattr(self.app.tmdb, method_name)(),
            self._show,
            self._error,
        )

    def _show(self, movies: list[Movie]) -> None:
        self._btn.configure(state="normal")
        if not movies:
            self._grid.show_message("No movies to show right now.")
            self._status.configure(text="Nothing to show.")
            return
        self._grid.set_movies(movies)
        self._status.configure(
            text=f"{len(movies)} movies. Click a poster to view details, rate or favourite it."
        )

    def _error(self, exc: Exception) -> None:
        self._btn.configure(state="normal")
        self._grid.show_message(f"Error: {exc}")
        self._status.configure(text=f"Error: {exc}")
