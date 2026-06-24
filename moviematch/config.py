"""Central configuration for MovieMatch.

Loads the TMDB API key from (in order of precedence):
  1. the ``TMDB_API_KEY`` environment variable, or
  2. a ``.env`` file in the project root (simple ``KEY=value`` parser).

Keeping all paths and constants here means the rest of the code never has to
guess where things live.
"""

from __future__ import annotations

import os
from pathlib import Path

# --- Paths -----------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
DATA_DIR = PROJECT_ROOT / "data_store"
DB_PATH = DATA_DIR / "moviematch.db"

# --- TMDB API --------------------------------------------------------------
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"
POSTER_SIZE = "w342"          # used in the details/search views
REQUEST_TIMEOUT = 10          # seconds


def _read_env_file(path: Path) -> dict[str, str]:
    """Tiny ``.env`` parser so we don't need an external dependency."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def get_api_key() -> str | None:
    """Return the TMDB API key, or ``None`` if it has not been configured."""
    key = os.environ.get("TMDB_API_KEY")
    if key:
        return key.strip()
    key = _read_env_file(ENV_FILE).get("TMDB_API_KEY")
    if key and key != "your_tmdb_api_key_here":
        return key
    return None


def ensure_data_dir() -> None:
    """Create the local data directory (for the SQLite DB) if needed."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def poster_url(poster_path: str | None) -> str | None:
    """Build a full poster URL from a TMDB ``poster_path`` fragment."""
    if not poster_path:
        return None
    return f"{TMDB_IMAGE_BASE}/{POSTER_SIZE}{poster_path}"
