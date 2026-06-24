"""Search tab: type a title, hit Enter, browse results, open details."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..models import Movie
from .components import run_async
from .poster_grid import PosterGrid


class SearchTab(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=10)
        self.app = app

        bar = ttk.Frame(self)
        bar.pack(fill="x")
        ttk.Label(bar, text="Search movies:").pack(side="left")
        self._entry = ttk.Entry(bar)
        self._entry.pack(side="left", fill="x", expand=True, padx=8)
        self._entry.bind("<Return>", lambda _e: self._search())
        self._btn = ttk.Button(bar, text="Search", command=self._search)
        self._btn.pack(side="left")

        self._status = ttk.Label(self, text="Type a title and press Enter.",
                                 foreground="#555")
        self._status.pack(anchor="w", pady=(8, 4))

        self._results = PosterGrid(self, on_open=self.app.open_details,
                                   poster_loader=self.app.poster_loader)
        self._results.pack(fill="both", expand=True)

        self._entry.focus_set()

    def _search(self) -> None:
        query = self._entry.get().strip()
        if not query:
            return
        self._status.configure(text=f"Searching for “{query}”…")
        self._btn.configure(state="disabled")

        run_async(
            self,
            lambda: self.app.tmdb.search(query),
            self._show_results,
            self._show_error,
        )

    def _show_results(self, movies: list[Movie]) -> None:
        self._btn.configure(state="normal")
        if not movies:
            self._results.show_message("No movies found.")
            self._status.configure(text="No results.")
            return
        self._results.set_movies(movies)
        self._status.configure(text=f"{len(movies)} result(s). Click a poster to open.")

    def _show_error(self, exc: Exception) -> None:
        self._btn.configure(state="normal")
        self._results.show_message("")
        self._status.configure(text=f"Error: {exc}")
