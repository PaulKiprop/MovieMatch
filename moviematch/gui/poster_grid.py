"""A responsive, scrollable grid of movie poster "cards".
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from ..models import Movie
from .components import run_async

# --- palette / sizing -------------------------------------------------------
BG = "#101319"          # page background (dark, makes posters pop)
CARD_BG = "#1c2130"     # card background
CARD_HOVER = "#2a3147"  # card background on hover
TEXT = "#f2f4f8"
SUBTEXT = "#93a0b5"
BADGE_BG = "#f5c518"    # IMDb-style gold
BADGE_FG = "#101319"

POSTER_SIZE = (150, 225)
CARD_W = POSTER_SIZE[0] + 16          # poster + inner padding
CARD_OUTER_W = CARD_W + 16            # + grid padding, used to compute columns


class _Card(tk.Frame):
    """A single movie card: poster + rating badge + title + year."""

    def __init__(self, master, movie: Movie, on_open, poster_loader, caption=""):
        super().__init__(master, bg=CARD_BG, bd=0, highlightthickness=0,
                         cursor="hand2", width=CARD_W)
        self.movie = movie
        self._on_open = on_open
        self._poster_loader = poster_loader

        # Poster area (fixed size) with the rating badge placed over it.
        holder = tk.Frame(self, bg=CARD_BG, width=POSTER_SIZE[0], height=POSTER_SIZE[1])
        holder.pack(padx=8, pady=(8, 4))
        holder.pack_propagate(False)

        self._poster = tk.Label(holder, bg="#0a0c10", fg=SUBTEXT, text="…",
                                font=("Segoe UI", 9))
        self._poster.place(x=0, y=0, relwidth=1, relheight=1)

        if movie.vote_average:
            badge = tk.Label(holder, text=f"★ {movie.vote_average:.1f}",
                             bg=BADGE_BG, fg=BADGE_FG, font=("Segoe UI", 9, "bold"),
                             padx=5, pady=1)
            badge.place(relx=1.0, rely=0.0, x=-4, y=4, anchor="ne")

        year = f"  ·  {movie.year}" if movie.year else ""
        title = tk.Label(self, text=movie.title, bg=CARD_BG, fg=TEXT,
                         font=("Segoe UI", 10, "bold"), wraplength=CARD_W - 12,
                         justify="left", anchor="w")
        title.pack(fill="x", padx=8)
        sub = tk.Label(self, text=(movie.genres[0] if movie.genres else "") + year,
                       bg=CARD_BG, fg=SUBTEXT, font=("Segoe UI", 8),
                       anchor="w")
        sub.pack(fill="x", padx=8, pady=(0, 8 if not caption else 0))

        hover_widgets = [self, holder, self._poster, title, sub]
        if caption:
            cap = tk.Label(self, text=caption, bg=CARD_BG, fg=BADGE_BG,
                           font=("Segoe UI", 8, "bold"), wraplength=CARD_W - 12,
                           justify="left", anchor="w")
            cap.pack(fill="x", padx=8, pady=(0, 8))
            hover_widgets.append(cap)

        # Hover + click apply to the whole card and every child widget.
        for w in hover_widgets:
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)
            w.bind("<Button-1>", lambda _e: self._on_open(self.movie))

    # ---- visuals ---------------------------------------------------------
    def _set_bg(self, color: str) -> None:
        self.configure(bg=color)
        for child in self.winfo_children():
            if isinstance(child, tk.Label):      # leave the poster holder dark
                child.configure(bg=color)

    def _on_enter(self, _e) -> None:
        self._set_bg(CARD_HOVER)

    def _on_leave(self, _e) -> None:
        self._set_bg(CARD_BG)

    # ---- poster loading --------------------------------------------------
    def load_poster(self) -> None:
        if not self._poster_loader.available:
            self._poster.configure(text="no image")
            return
        run_async(
            self,
            lambda: self._poster_loader.fetch(self.movie.poster_path, POSTER_SIZE),
            self._apply_poster,
            lambda _exc: self._poster.configure(text="no image"),
        )

    def _apply_poster(self, key) -> None:
        if not self.winfo_exists():
            return
        photo = self._poster_loader.photo(key)
        if photo is None:
            self._poster.configure(text="no image")
            return
        self._poster.configure(image=photo, text="")
        self._poster.image = photo   # keep a reference so it isn't GC'd


class PosterGrid(ttk.Frame):
    """Scrollable, reflowing container of :class:`_Card` widgets."""

    def __init__(self, master, on_open: Callable[[Movie], None], poster_loader):
        super().__init__(master)
        self.on_open = on_open
        self.poster_loader = poster_loader
        self._cards: list[_Card] = []
        self._cols = 0
        self._message_label = None

        self._canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scrollbar.set)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._inner = tk.Frame(self._canvas, bg=BG)
        self._window = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")

        self._inner.bind(
            "<Configure>",
            lambda _e: self._canvas.configure(scrollregion=self._canvas.bbox("all")),
        )
        self._canvas.bind("<Configure>", self._on_canvas_resize)
        # Scroll with the mouse wheel only while the pointer is over the grid.
        self._canvas.bind("<Enter>", lambda _e: self._canvas.bind_all("<MouseWheel>", self._on_wheel))
        self._canvas.bind("<Leave>", lambda _e: self._canvas.unbind_all("<MouseWheel>"))

    # ---- scrolling / layout ---------------------------------------------
    def _on_wheel(self, event) -> None:
        self._canvas.yview_scroll(int(-event.delta / 120), "units")

    def _on_canvas_resize(self, event) -> None:
        self._canvas.itemconfigure(self._window, width=event.width)
        cols = max(1, event.width // CARD_OUTER_W)
        if cols != self._cols:
            self._cols = cols
            self._reflow()

    def _reflow(self) -> None:
        if not self._cards or self._cols == 0:
            return
        for index, card in enumerate(self._cards):
            card.grid(row=index // self._cols, column=index % self._cols,
                      padx=8, pady=8, sticky="n")

    # ---- public API ------------------------------------------------------
    def set_movies(self, movies: list[Movie], captions: dict[int, str] | None = None) -> None:
        captions = captions or {}
        self._clear()
        for movie in movies:
            card = _Card(self._inner, movie, self.on_open, self.poster_loader,
                         caption=captions.get(movie.id, ""))
            self._cards.append(card)
        if self._cols == 0:
            self._cols = max(1, self._canvas.winfo_width() // CARD_OUTER_W)
        self._reflow()
        for card in self._cards:        # kick off lazy poster loads
            card.load_poster()

    def show_message(self, message: str) -> None:
        self._clear()
        self._message_label = tk.Label(self._inner, text=message, bg=BG, fg=SUBTEXT,
                                       font=("Segoe UI", 11), pady=30)
        self._message_label.grid(row=0, column=0, padx=20, sticky="w")

    def _clear(self) -> None:
        for card in self._cards:
            card.destroy()
        self._cards.clear()
        if self._message_label is not None:
            self._message_label.destroy()
            self._message_label = None
