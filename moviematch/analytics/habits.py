"""Watching-habit analytics.

Pure functions that turn the user's stored favourites / ratings / history into
plain Python summaries. Keeping these free of any GUI or matplotlib code makes
them easy to unit-test; the GUI layer is what turns them into charts.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from ..data.storage import Storage
from ..models import Movie


@dataclass
class HabitsReport:
    """A snapshot of the user's viewing habits."""

    total_favorites: int = 0
    total_rated: int = 0
    total_views: int = 0
    average_rating: float | None = None
    genre_counts: Counter = field(default_factory=Counter)      # genre -> count
    decade_counts: Counter = field(default_factory=Counter)     # "1990s" -> count
    rating_distribution: Counter = field(default_factory=Counter)  # 1..5 -> count
    top_genre: str | None = None

    @property
    def is_empty(self) -> bool:
        return self.total_favorites == 0 and self.total_rated == 0 and self.total_views == 0


def _accumulate_genres(movies: list[Movie], counter: Counter) -> None:
    for m in movies:
        for g in m.genres:
            counter[g] += 1


def build_report(storage: Storage) -> HabitsReport:
    """Compute a :class:`HabitsReport` from everything in storage."""
    favorites = storage.list_favorites()
    ratings = storage.list_ratings()          # list[(Movie, rating)]
    history = storage.list_history()           # list[(Movie, viewed_at)]

    report = HabitsReport(
        total_favorites=len(favorites),
        total_rated=len(ratings),
        total_views=len(history),
    )

    # Genres + decades are drawn from the union of everything the user engaged
    # with, de-duplicated by movie id so one movie isn't counted many times.
    engaged: dict[int, Movie] = {}
    for m in favorites:
        engaged[m.id] = m
    for m, _ in ratings:
        engaged[m.id] = m
    for m, _ in history:
        engaged.setdefault(m.id, m)

    _accumulate_genres(list(engaged.values()), report.genre_counts)
    for m in engaged.values():
        if m.decade:
            report.decade_counts[m.decade] += 1

    if ratings:
        for _, r in ratings:
            report.rating_distribution[r] += 1
        report.average_rating = sum(r for _, r in ratings) / len(ratings)

    if report.genre_counts:
        report.top_genre = report.genre_counts.most_common(1)[0][0]

    return report
