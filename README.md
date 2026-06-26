# MovieMatch 🎬

**Intelligent Movie Recommendation System** — a desktop application that helps
you discover movies based on your preferences and viewing history.

Built with Python + Tkinter, powered by the [TMDB](https://www.themoviedb.org)
API, with a content-based recommendation engine.

## Features

| Feature | Where |
|---|---|
| 🏠 **Discover latest movies** on launch | *Home* tab (loads automatically) |
| 🔍 **Search movies** by title | *Search* tab |
| 📄 **View movie details** (overview, genres, poster, score) | click any poster / movie |
| ⭐ **Rate movies** (1–5 stars) | movie details window |
| ❤️ **Save favourites** | movie details window |
| 🤝 **Receive recommendations** based on your taste | *Recommendations* tab |
| 📊 **Analyze your watching habits** (charts) | *Analytics* tab |

## Project structure

```
MovieMatch/
├── main.py                       # entry point
├── requirements.txt
├── .env.example                  # template for your API key
├── tests/test_core.py            # offline unit tests (no network/GUI)
└── moviematch/
    ├── config.py                 # key loading, paths, constants
    ├── models.py                 # the Movie dataclass
    ├── api/tmdb_client.py         # TMDB REST wrapper
    ├── data/storage.py            # SQLite: movies, favourites, ratings, history
    ├── recommender/content_based.py   # cosine-similarity taste matching
    ├── analytics/habits.py        # habit aggregation (pure functions)
    └── gui/                       # Tkinter UI (app + 5 tabs + details window)
```

The design separates concerns into layers — **API**, **storage**,
**recommender**, **analytics**, and **GUI** — so each can be understood and
tested on its own.

## Setup

1. **Create a virtual environment and install dependencies**

   ```bash
   python -m venv .venv
   .venv\Scripts\activate          # Windows
   # source .venv/bin/activate     # macOS/Linux
   pip install -r requirements.txt
   ```

2. **Get a free TMDB API key**

   - Sign up at <https://www.themoviedb.org/signup>
   - Go to **Settings → API** and request an API key (v3 auth).

3. **Configure the key**

   - Copy `.env.example` to `.env`
   - Paste your key:  `TMDB_API_KEY=xxxxxxxxxxxxxxxxxxxx`

   (Alternatively set the `TMDB_API_KEY` environment variable.)

## Run

```bash
python main.py
```

> The app still launches without an API key — your saved favourites and
> analytics work offline — but search and recommendations need the key.

## How recommendations work

1. Every movie you **favourite** or **rate highly** feeds a *taste profile*: a
   weighted bag of genres and keywords (a 5-star movie counts more than a
   3-star one; genres count more than individual keywords).
2. Candidate movies are pulled from TMDB (your top genres + popular titles).
3. Each candidate is scored by **cosine similarity** to your profile, and the
   movies you've already seen are excluded.
4. Results are shown with a *match %* and the **reasons** they were picked
   (the shared genres/keywords) — so recommendations are explainable.

## Offline mode (no API key needed)

The repository ships with a bundled dataset of real TMDB movies in
`data_store/movies_offline.json`.  When MovieMatch starts and **no API key is
found**, it automatically switches to this local dataset — all features work:

| Feature | Offline behaviour |
|---|---|
| 🏠 Home (Now Playing / Popular / Top Rated) | Served from local dataset |
| 🔍 Search | Case-insensitive title search in local dataset |
| ❤️ Favourites & ⭐ Ratings | Fully functional (stored in SQLite as usual) |
| 🤝 Recommendations | Content-based engine runs on local dataset |
| 📊 Analytics | Fully functional |

A one-time info dialog is shown on launch to let the user know they are in
offline mode.

### Re-generating the offline dataset

If you want to refresh the bundled data with the latest movies from TMDB
(requires your own API key):

```bash
python scripts/seed_offline.py
```

This fetches ~240 movies across the Popular, Top-Rated, Now-Playing, and
Upcoming endpoints (3 pages each), including full details and keywords for the
recommendation engine, and writes them to `data_store/movies_offline.json`.
Commit the updated file to the repository afterwards.

---

## Tests

```bash
python -m unittest discover -s tests -v
```

Covers the model, storage, recommender and analytics layers — no network or
display required.
