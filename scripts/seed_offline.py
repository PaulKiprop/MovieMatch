"""
scripts/seed_offline.py
=======================
Run this script ONCE (with your TMDB API key configured) to fetch real movie
data from TMDB and save it to data_store/movies_offline.json.

That JSON file is then committed to the repo so reviewers who clone the project
can use the app without their own API key.

Usage:
    python scripts/seed_offline.py

Requirements:
    - A valid TMDB API key in .env  (TMDB_API_KEY=...)
    - requests installed  (pip install -r requirements.txt)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Allow running from the project root without installing the package.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from moviematch.api.tmdb_client import TMDBClient, TMDBError  # noqa: E402
from moviematch import config  # noqa: E402

OUTPUT_PATH = PROJECT_ROOT / "data_store" / "movies_offline.json"

# How many pages to pull from each endpoint (20 movies per page).
PAGES = 3


def _movie_to_dict(movie) -> dict:
    """Serialise a Movie dataclass to a plain dict for JSON storage."""
    return {
        "id":           movie.id,
        "title":        movie.title,
        "overview":     movie.overview,
        "release_date": movie.release_date,
        "poster_path":  movie.poster_path,
        "vote_average": movie.vote_average,
        "genres":       movie.genres,
        "keywords":     movie.keywords,
    }


def main() -> None:
    print("Connecting to TMDB…")
    try:
        client = TMDBClient()
    except TMDBError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    seen: dict[int, dict] = {}   # keyed by movie id to deduplicate

    endpoints = [
        ("popular",     client.popular),
        ("top_rated",   client.top_rated),
        ("now_playing", client.now_playing),
        ("upcoming",    client.upcoming),
    ]

    for label, fetch in endpoints:
        for page in range(1, PAGES + 1):
            print(f"  Fetching {label} page {page}…", end=" ")
            try:
                movies = fetch(page=page)
            except TMDBError as exc:
                print(f"SKIP ({exc})")
                continue

            # Fetch full details (includes keywords) for each movie.
            for movie in movies:
                if movie.id in seen:
                    continue
                try:
                    detailed = client.details(movie.id)
                    seen[detailed.id] = _movie_to_dict(detailed)
                except TMDBError:
                    # Fall back to the search-result data if details fail.
                    seen[movie.id] = _movie_to_dict(movie)

            print(f"{len(movies)} movies ({len(seen)} total unique so far)")

    config.ensure_data_dir()
    records = list(seen.values())
    OUTPUT_PATH.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nDone — {len(records)} movies saved to {OUTPUT_PATH}")
    print("Commit data_store/movies_offline.json to your repository.")


if __name__ == "__main__":
    main()
