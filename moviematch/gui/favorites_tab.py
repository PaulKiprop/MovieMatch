"""Favourites tab: the movies the user has saved, with quick access."""

from __future__ import annotations

from tkinter import ttk

from .poster_grid import PosterGrid


class FavoritesTab(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=10)
        self.app = app

        header = ttk.Frame(self)
        header.pack(fill="x")
        ttk.Label(header, text="Your favourites", font=("Segoe UI", 12, "bold")).pack(
            side="left"
        )
        ttk.Button(header, text="Refresh", command=self.refresh).pack(side="right")

        self._status = ttk.Label(self, text="", foreground="#555")
        self._status.pack(anchor="w", pady=(6, 4))

        self._grid = PosterGrid(self, on_open=self.app.open_details,
                                poster_loader=self.app.poster_loader)
        self._grid.pack(fill="both", expand=True)

    def refresh(self) -> None:
        """Reload favourites from storage (cheap, local — no thread needed)."""
        favorites = self.app.storage.list_favorites()
        if not favorites:
            self._grid.show_message("No favourites yet — add some from a movie's details.")
            self._status.configure(text="0 favourites.")
            return
        self._grid.set_movies(favorites)
        self._status.configure(text=f"{len(favorites)} favourite(s). Click a poster to open.")
