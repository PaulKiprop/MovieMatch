"""The movie details window.

Opened when a user activates a movie anywhere in the app. Shows full metadata
"""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from ..models import Movie
from .components import StarRating, run_async


class DetailsWindow(tk.Toplevel):
    def __init__(self, app, movie: Movie):
        super().__init__(app.root)
        self.app = app
        self.movie = movie
        self.title(movie.title)
        self.geometry("640x460")
        self.transient(app.root)
        self.minsize(560, 400)

        self._poster_label = None
        self._build()
        # Fetch full details (keywords/genres) and a poster in the background.
        self._load_full_details()

    # ---- layout ----------------------------------------------------------
    def _build(self) -> None:
        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)

        # Left: poster
        left = ttk.Frame(container)
        left.pack(side="left", fill="y", padx=(0, 12))
        self._poster_label = ttk.Label(left, text="(loading poster…)", anchor="center",
                                       width=22)
        self._poster_label.pack()

        # Right: text + controls
        right = ttk.Frame(container)
        right.pack(side="left", fill="both", expand=True)

        year = f"  ({self.movie.year})" if self.movie.year else ""
        ttk.Label(right, text=self.movie.title + year,
                  font=("Segoe UI", 15, "bold"), wraplength=380,
                  justify="left").pack(anchor="w")

        self._meta_label = ttk.Label(right, text="", foreground="#555")
        self._meta_label.pack(anchor="w", pady=(2, 8))

        self._overview = tk.Text(right, height=8, wrap="word", relief="flat",
                                 background=self.cget("background"),
                                 font=("Segoe UI", 10))
        self._overview.insert("1.0", self.movie.overview or "No overview available.")
        self._overview.configure(state="disabled")
        self._overview.pack(fill="both", expand=True)

        # Controls row
        controls = ttk.Frame(right)
        controls.pack(fill="x", pady=(10, 0))

        ttk.Label(controls, text="Your rating:").grid(row=0, column=0, sticky="w")
        self._stars = StarRating(controls, command=self._on_rate)
        self._stars.grid(row=0, column=1, sticky="w", padx=(6, 0))
        existing = self.app.storage.get_rating(self.movie.id)
        if existing:
            self._stars.set(existing)

        self._fav_btn = ttk.Button(controls, text="", command=self._toggle_favorite)
        self._fav_btn.grid(row=0, column=2, padx=(20, 0))
        self._refresh_fav_button()

        ttk.Button(controls, text="Close", command=self.destroy).grid(
            row=0, column=3, padx=(10, 0)
        )

        # Viewing the details counts as "watched" for analytics.
        self.app.storage.log_view(self.movie)

    # ---- async loads -----------------------------------------------------
    def _load_full_details(self) -> None:
        run_async(
            self,
            lambda: self.app.tmdb.details(self.movie.id),
            self._apply_full_details,
            lambda exc: self._meta_label.configure(
                text="(could not load full details)"
            ),
        )

    def _apply_full_details(self, full: Movie) -> None:
        self.movie = full
        self.app.storage.upsert_movie(full)        # cache richer metadata
        genres = ", ".join(full.genres) if full.genres else "Unknown genres"
        score = f"★ {full.vote_average:.1f}/10" if full.vote_average else ""
        self._meta_label.configure(text=f"{genres}    {score}".strip())
        if self.movie.overview:
            self._overview.configure(state="normal")
            self._overview.delete("1.0", tk.END)
            self._overview.insert("1.0", self.movie.overview)
            self._overview.configure(state="disabled")
        self._load_poster()

    def _load_poster(self) -> None:
        if not self.app.poster_loader.available:
            self._poster_label.configure(text="(install Pillow\nto see posters)")
            return
        run_async(
            self,
            lambda: self.app.poster_loader.fetch(self.movie.poster_path, size=(185, 278)),
            self._apply_poster,
            lambda exc: self._poster_label.configure(text="(no poster)"),
        )

    def _apply_poster(self, key) -> None:
        photo = self.app.poster_loader.photo(key)
        if photo is None:
            self._poster_label.configure(text="(no poster)")
            return
        self._poster_label.configure(image=photo, text="")
        self._poster_label.image = photo   # keep a reference

    # ---- actions ---------------------------------------------------------
    def _on_rate(self, value: int) -> None:
        self.app.storage.set_rating(self.movie, value)
        self.app.notify_data_changed()

    def _toggle_favorite(self) -> None:
        if self.app.storage.is_favorite(self.movie.id):
            self.app.storage.remove_favorite(self.movie.id)
        else:
            self.app.storage.add_favorite(self.movie)
        self._refresh_fav_button()
        self.app.notify_data_changed()

    def _refresh_fav_button(self) -> None:
        fav = self.app.storage.is_favorite(self.movie.id)
        self._fav_btn.configure(text="♥ Remove favourite" if fav else "♡ Add favourite")
