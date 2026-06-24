"""Analytics tab: visualise the user's viewing habits with matplotlib charts
embedded directly in the Tkinter window."""

from __future__ import annotations

from tkinter import ttk

import matplotlib

matplotlib.use("TkAgg")  # must be set before importing pyplot/backends
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from ..analytics.habits import HabitsReport, build_report


class AnalyticsTab(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master, padding=10)
        self.app = app

        header = ttk.Frame(self)
        header.pack(fill="x")
        ttk.Label(header, text="Your watching habits",
                  font=("Segoe UI", 12, "bold")).pack(side="left")
        ttk.Button(header, text="Refresh", command=self.refresh).pack(side="right")

        self._summary = ttk.Label(self, text="", foreground="#333")
        self._summary.pack(anchor="w", pady=(6, 4))

        self._figure = Figure(figsize=(7, 4.2), dpi=100)
        self._canvas = FigureCanvasTkAgg(self._figure, master=self)
        self._canvas.get_tk_widget().pack(fill="both", expand=True)

    def refresh(self) -> None:
        report = build_report(self.app.storage)
        self._render_summary(report)
        self._render_charts(report)

    # ---- text summary ----------------------------------------------------
    def _render_summary(self, r: HabitsReport) -> None:
        if r.is_empty:
            self._summary.configure(
                text="No activity yet. Search, rate and favourite movies to see insights."
            )
            return
        avg = f"{r.average_rating:.1f}/5" if r.average_rating is not None else "—"
        self._summary.configure(
            text=(
                f"Favourites: {r.total_favorites}    "
                f"Rated: {r.total_rated}    "
                f"Movies viewed: {r.total_views}    "
                f"Avg rating: {avg}    "
                f"Top genre: {r.top_genre or '—'}"
            )
        )

    # ---- charts ----------------------------------------------------------
    def _render_charts(self, r: HabitsReport) -> None:
        self._figure.clear()

        if r.is_empty:
            ax = self._figure.add_subplot(111)
            ax.text(0.5, 0.5, "No data to chart yet", ha="center", va="center")
            ax.axis("off")
            self._canvas.draw()
            return

        ax1 = self._figure.add_subplot(131)
        self._bar(ax1, r.genre_counts.most_common(6), "Top genres", "#4c72b0", rotate=True)

        ax2 = self._figure.add_subplot(132)
        dist = [(str(star), r.rating_distribution.get(star, 0)) for star in range(1, 6)]
        self._bar(ax2, dist, "Ratings given", "#dd8452")
        ax2.set_xlabel("stars")

        ax3 = self._figure.add_subplot(133)
        decades = sorted(r.decade_counts.items())
        self._bar(ax3, decades, "By decade", "#55a868", rotate=True)

        self._figure.tight_layout()
        self._canvas.draw()

    @staticmethod
    def _bar(ax, pairs, title, color, rotate=False) -> None:
        ax.set_title(title, fontsize=10)
        if not pairs:
            ax.text(0.5, 0.5, "n/a", ha="center", va="center", transform=ax.transAxes)
            ax.axis("off")
            return
        labels = [str(k) for k, _ in pairs]
        values = [v for _, v in pairs]
        ax.bar(labels, values, color=color)
        ax.set_ylabel("count")
        if rotate:
            ax.tick_params(axis="x", labelrotation=40, labelsize=8)
        # Whole-number y ticks only.
        top = max(values)
        ax.set_yticks(range(0, top + 1, max(1, top // 5)))
