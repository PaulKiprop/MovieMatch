"""The MovieMatch main window — owns shared services and hosts the tabs."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from ..api.tmdb_client import TMDBClient, TMDBError
from ..data.storage import Storage
from ..models import Movie
from .analytics_tab import AnalyticsTab
from .components import PosterLoader
from .details import DetailsWindow
from .favorites_tab import FavoritesTab
from .home_tab import HomeTab
from .recommend_tab import RecommendTab
from .search_tab import SearchTab


class _NullClient:
    """Stand-in used when no API key is configured: every call fails with a
    clear, actionable message instead of an obscure ``AttributeError``."""

    def __init__(self, message: str):
        self._message = message

    def __getattr__(self, _name):
        def _fail(*_args, **_kwargs):
            raise TMDBError(self._message)
        return _fail


class MovieMatchApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("MovieMatch — Intelligent Movie Recommendations")
        self.root.geometry("860x600")
        self.root.minsize(720, 520)

        self.storage = Storage()
        self.poster_loader = PosterLoader()
        self.tmdb = self._init_tmdb()

        self._build_tabs()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---- services --------------------------------------------------------
    def _init_tmdb(self):
        try:
            return TMDBClient()
        except TMDBError as exc:
            messagebox.showwarning(
                "TMDB API key needed",
                f"{exc}\n\nSearch and recommendations are disabled until a key is "
                "configured. Your saved favourites and analytics still work.",
            )
            return _NullClient(str(exc))

    # ---- layout ----------------------------------------------------------
    def _build_tabs(self) -> None:
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True)

        self.home_tab = HomeTab(notebook, self)
        self.search_tab = SearchTab(notebook, self)
        self.favorites_tab = FavoritesTab(notebook, self)
        self.recommend_tab = RecommendTab(notebook, self)
        self.analytics_tab = AnalyticsTab(notebook, self)

        notebook.add(self.home_tab, text="Home")
        notebook.add(self.search_tab, text="Search")
        notebook.add(self.favorites_tab, text="Favourites")
        notebook.add(self.recommend_tab, text="Recommendations")
        notebook.add(self.analytics_tab, text="Analytics")

        # Refresh the local-data tabs whenever they become visible.
        notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self._notebook = notebook

        self.favorites_tab.refresh()
        # Populate the landing page with the latest movies as soon as we open.
        if not isinstance(self.tmdb, _NullClient):
            self.root.after(100, self.home_tab.load)

    def _on_tab_changed(self, _event) -> None:
        current = self._notebook.nametowidget(self._notebook.select())
        if current is self.favorites_tab:
            self.favorites_tab.refresh()
        elif current is self.analytics_tab:
            self.analytics_tab.refresh()

    # ---- shared actions --------------------------------------------------
    def open_details(self, movie: Movie) -> None:
        DetailsWindow(self, movie)

    def notify_data_changed(self) -> None:
        """Called after a favourite/rating change so other tabs stay in sync."""
        self.favorites_tab.refresh()
        self.analytics_tab.refresh()

    def _on_close(self) -> None:
        self.storage.close()
        self.root.destroy()


def launch() -> None:
    root = tk.Tk()
    MovieMatchApp(root)
    root.mainloop()
