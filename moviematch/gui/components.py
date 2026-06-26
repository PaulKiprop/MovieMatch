"""Reusable Tkinter building blocks shared across the tabs.

Includes:
  * :func:`run_async`        - run blocking work (API calls) off the UI thread
  * :class:`PosterLoader`    - download + cache movie posters as Tk images
  * :class:`StarRating`      - a clickable 1-5 star widget
  * :class:`MovieList`       - a scrollable, selectable list of movies
"""

from __future__ import annotations

import io
import threading
import tkinter as tk
from tkinter import ttk
from typing import Callable

import requests

from .. import config
from ..models import Movie

# Pillow is required to show TMDB's JPEG posters in Tkinter.
try:
    from PIL import Image, ImageTk
    _HAS_PIL = True
except ImportError:  # pragma: no cover - graceful fallback
    _HAS_PIL = False


def run_async(
    widget: tk.Misc,
    work: Callable[[], object],
    on_success: Callable[[object], None],
    on_error: Callable[[Exception], None],
) -> None:
    """Run ``work()`` in a background thread, then deliver the result on the
    Tk main thread via ``widget.after`` (Tkinter is not thread-safe)."""

    def runner() -> None:
        try:
            result = work()
        except Exception as exc:  # noqa: BLE001 - surfaced to on_error
            widget.after(0, lambda exc=exc: on_error(exc))
        else:
            widget.after(0, lambda result=result: on_success(result))

    threading.Thread(target=runner, daemon=True).start()


class PosterLoader:
    """Downloads + caches movie posters.

    The work is split in two on purpose:
      * :meth:`fetch`  does the network I/O and image decoding — safe to call
        from a background thread.
      * :meth:`photo`  turns the decoded image into a Tk ``PhotoImage`` — this
        MUST run on the Tk main thread, because creating Tk image objects off
        the main thread is not safe.
    """

    def __init__(self) -> None:
        self._image_cache: dict[str, "Image.Image"] = {}   # decoded PIL images
        self._photo_cache: dict[str, object] = {}          # Tk PhotoImages
        self._lock = threading.Lock()

    @property
    def available(self) -> bool:
        return _HAS_PIL

    def fetch(self, poster_path: str | None, size=(150, 225)) -> str | None:
        """Background-thread step: download and resize the poster, returning a
        cache key (or ``None`` if unavailable). Does NOT create a Tk image."""
        if not _HAS_PIL:
            return None
        url = config.poster_url(poster_path)
        if not url:
            return None
        key = f"{url}@{size[0]}x{size[1]}"
        with self._lock:
            if key in self._image_cache:
                return key
        try:
            resp = requests.get(url, timeout=config.REQUEST_TIMEOUT)
            resp.raise_for_status()
            image = Image.open(io.BytesIO(resp.content)).convert("RGB")
            image = image.resize(size, Image.LANCZOS)
        except Exception:  # noqa: BLE001 - posters are non-critical
            return None
        with self._lock:
            self._image_cache[key] = image
        return key

    def photo(self, key: str | None):
        """Main-thread step: return a cached Tk ``PhotoImage`` for ``key``."""
        if not key:
            return None
        if key in self._photo_cache:
            return self._photo_cache[key]
        with self._lock:
            image = self._image_cache.get(key)
        if image is None:
            return None
        photo = ImageTk.PhotoImage(image)
        self._photo_cache[key] = photo
        return photo


class StarRating(ttk.Frame):
    """A row of five clickable stars representing a 1-5 rating."""

    FILLED = "★"   # ★
    EMPTY = "☆"    # ☆

    def __init__(self, master, command: Callable[[int], None] | None = None):
        super().__init__(master)
        self._command = command
        self._rating = 0
        self._buttons: list[tk.Label] = []
        for i in range(1, 6):
            lbl = tk.Label(self, text=self.EMPTY, font=("Segoe UI", 18), cursor="hand2")
            lbl.grid(row=0, column=i, padx=1)
            lbl.bind("<Button-1>", lambda _e, v=i: self._on_click(v))
            lbl.bind("<Enter>", lambda _e, v=i: self._preview(v))
            lbl.bind("<Leave>", lambda _e: self._render(self._rating))
            self._buttons.append(lbl)

    def _on_click(self, value: int) -> None:
        self.set(value)
        if self._command:
            self._command(value)

    def _preview(self, value: int) -> None:
        self._render(value, color="#e0a800")

    def _render(self, value: int, color: str = "#f5c518") -> None:
        for idx, lbl in enumerate(self._buttons, start=1):
            filled = idx <= value
            lbl.configure(text=self.FILLED if filled else self.EMPTY,
                          fg=color if filled else "#999999")

    def set(self, value: int) -> None:
        self._rating = value
        self._render(value)

    def get(self) -> int:
        return self._rating


class MovieList(ttk.Frame):
    """A scrollable listbox of movies with title + year + score, plus a
    callback when the selection is opened (double-click or Enter)."""

    def __init__(self, master, on_open: Callable[[Movie], None]):
        super().__init__(master)
        self._on_open = on_open
        self._movies: list[Movie] = []

        self._listbox = tk.Listbox(self, activestyle="dotbox", font=("Segoe UI", 10))
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=scrollbar.set)
        self._listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)

        self._listbox.bind("<Double-Button-1>", self._open_selected)
        self._listbox.bind("<Return>", self._open_selected)

    def set_movies(self, movies: list[Movie], annotate: Callable[[Movie], str] | None = None) -> None:
        """Replace the displayed list. ``annotate`` optionally appends a suffix
        (e.g. a recommendation reason) to each row."""
        self._movies = movies
        self._listbox.delete(0, tk.END)
        for m in movies:
            year = f" ({m.year})" if m.year else ""
            suffix = f"  —  {annotate(m)}" if annotate else ""
            self._listbox.insert(tk.END, f"{m.title}{year}{suffix}")

    def _open_selected(self, _event=None) -> None:
        selection = self._listbox.curselection()
        if selection:
            self._on_open(self._movies[selection[0]])

    def show_message(self, message: str) -> None:
        self._movies = []
        self._listbox.delete(0, tk.END)
        self._listbox.insert(tk.END, message)
