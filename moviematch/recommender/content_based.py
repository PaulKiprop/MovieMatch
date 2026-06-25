"""Content-based recommendation engine.

"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

from ..models import Movie


@dataclass
class Recommendation:
    """A recommended movie plus the human-readable reason it was chosen."""

    movie: Movie
    score: float
    reasons: list[str]


# Genres describe taste more strongly than individual keywords, so weight them.
GENRE_WEIGHT = 3.0
KEYWORD_WEIGHT = 1.0


def _feature_vector(movie: Movie) -> Counter:
    """Turn a movie into a weighted bag of features."""
    vec: Counter = Counter()
    for g in movie.genres:
        vec[f"g:{g}"] += GENRE_WEIGHT
    for k in movie.keywords:
        vec[f"k:{k}"] += KEYWORD_WEIGHT
    return vec


def build_profile(liked: list[tuple[Movie, float]]) -> Counter:
    """Aggregate liked movies into one weighted taste profile.

    ``liked`` is a list of ``(movie, weight)`` pairs where ``weight`` reflects
    how much the user liked it (e.g. a 5-star rating weighs more than a 3-star).
    """
    profile: Counter = Counter()
    for movie, weight in liked:
        for feature, value in _feature_vector(movie).items():
            profile[feature] += value * weight
    return profile


def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0
    common = set(a) & set(b)
    dot = sum(a[f] * b[f] for f in common)
    if dot == 0:
        return 0.0
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    return dot / (norm_a * norm_b)


def _reasons(profile: Counter, candidate: Movie, limit: int = 3) -> list[str]:
    """Explain a match: which of the user's favourite features it shares."""
    cand = _feature_vector(candidate)
    shared = [(f, profile[f]) for f in cand if f in profile]
    shared.sort(key=lambda x: x[1], reverse=True)
    labels = []
    for feature, _ in shared[:limit]:
        kind, _, name = feature.partition(":")
        labels.append(name if kind == "g" else name)
    return labels


def recommend(
    liked: list[tuple[Movie, float]],
    candidates: list[Movie],
    *,
    exclude_ids: set[int] | None = None,
    top_n: int = 20,
) -> list[Recommendation]:
    """Rank ``candidates`` against the taste profile built from ``liked``.

    Movies in ``exclude_ids`` (already seen/rated/favourited) are skipped.
    Candidates that share no features with the profile are dropped.
    """
    exclude_ids = exclude_ids or set()
    profile = build_profile(liked)
    if not profile:
        return []

    results: list[Recommendation] = []
    for cand in candidates:
        if cand.id in exclude_ids:
            continue
        score = _cosine(profile, _feature_vector(cand))
        if score <= 0:
            continue
        results.append(
            Recommendation(movie=cand, score=score, reasons=_reasons(profile, cand))
        )

    results.sort(key=lambda r: r.score, reverse=True)
    return results[:top_n]
