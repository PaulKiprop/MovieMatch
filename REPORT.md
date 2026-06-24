# MovieMatch — Intelligent Movie Recommendation System
### Project Report

**Module:** Computer Programming in Python · GISMA  
**Application type:** Desktop GUI application (Python + Tkinter)

---

## 1. Introduction

MovieMatch is a desktop application that helps users discover films based on
their personal tastes and viewing history. Rather than browsing endless lists,
the user builds up a profile simply by rating and saving the movies they like,
and the application responds with tailored, explainable recommendations.

The project demonstrates a complete, layered Python application: a live
connection to a real web API, local data persistence, a content-based
recommendation algorithm, data analytics with charts, and a responsive
graphical user interface — all organised into clearly separated modules.

The six core capabilities delivered are:

1. **Discover** the latest movies automatically on launch (Home page)
2. **Search** for movies by title
3. **View movie details** (overview, genres, poster, community score)
4. **Save favourites** and **rate** movies (1–5 stars)
5. **Receive recommendations** based on taste, with reasons
6. **Analyse watching habits** through visual charts

---

## 2. Implementation Stack

| Layer | Technology | Why it was chosen |
|---|---|---|
| Language | **Python 3.14** | Module requirement; rich standard library |
| GUI | **Tkinter / ttk** | Built into Python — no install needed, runs anywhere, ideal for a portable submission |
| Movie data | **TMDB REST API** | Free, well-documented source of real movie metadata, posters and ratings |
| HTTP client | **requests** | Clean, reliable API calls |
| Images | **Pillow (PIL)** | Decodes and resizes TMDB's JPEG posters for display in Tkinter |
| Charts | **matplotlib** | Embeds analytics charts directly inside the Tkinter window |
| Storage | **SQLite (`sqlite3`)** | Zero-configuration local database; part of the standard library |

External dependencies are limited to three well-established packages
(`requests`, `Pillow`, `matplotlib`), all listed in `requirements.txt`.

---

## 3. Architecture

The code is organised into a Python package, `moviematch`, with each concern
isolated in its own sub-module. This separation makes the system easy to
understand, test and extend.

```
moviematch/
├── config.py                   # API key loading, paths, constants
├── models.py                   # the Movie dataclass (shared everywhere)
├── api/tmdb_client.py          # TMDB REST wrapper
├── data/storage.py             # SQLite persistence layer
├── recommender/content_based.py# recommendation algorithm
├── analytics/habits.py         # habit aggregation (pure functions)
└── gui/                        # Tkinter UI: app + 5 tabs + details window
```

**Design principles applied:**

- **Single source of truth** — one `Movie` dataclass is used by every layer
  (API, storage, recommender, analytics), so all parts of the system speak the
  same language.
- **Separation of concerns** — networking, storage, logic and presentation
  never mix. For example, the analytics module contains only pure functions
  with no GUI code, which makes it directly unit-testable.
- **Responsiveness** — all network calls (search, recommendations, poster
  downloads) run on background threads via a `run_async` helper, so the
  interface never freezes. Results are safely delivered back to the main thread
  using Tkinter's `after()` mechanism.
- **Graceful degradation** — if no API key is configured, the app still opens;
  saved favourites and analytics continue to work offline, and the online
  features show a clear, actionable message instead of crashing.

---

## 4. Key Features in Detail

### 4.1 Home (discovery) page
On startup the app automatically loads the latest cinema releases into a
**responsive poster grid**. A dropdown lets the user switch between *Now Playing*,
*Popular*, *Top Rated* and *Upcoming*. Each film appears as a card showing its
poster, a gold IMDb-style rating badge, and its title — posters load lazily so
the page appears instantly and fills in as images arrive.

### 4.2 Search and details
The user searches by title; results appear in the same poster grid. Clicking any
poster opens a **details window** with the full overview, genres, poster, and
community score, plus controls to rate the movie and add/remove it as a
favourite.

### 4.3 Favourites and ratings
Favourites and 1–5 star ratings are stored in the local SQLite database and
persist between sessions. Viewing a movie's details is also logged, building the
history used by the analytics and recommendation features.

### 4.4 Recommendations *(content-based)*
The recommendation engine works in four explainable steps:

1. **Build a taste profile** — every favourited or highly-rated movie
   contributes a weighted "bag" of genres and keywords. A 5-star film counts
   more than a 3-star one, genres count more than individual keywords, and films
   rated 1–2 stars are *down-weighted* so dislikes do not pollute the profile.
2. **Gather candidates** — fresh movies are pulled from TMDB based on the user's
   top genres, plus popular titles to broaden the pool.
3. **Score** each candidate against the profile using **cosine similarity**, and
   exclude anything the user has already seen.
4. **Explain** — each recommendation is shown with a *match %* and the shared
   genres/keywords that earned it a place, so the suggestions are transparent
   rather than a "black box".

### 4.5 Analytics
The Analytics tab summarises viewing habits and renders three matplotlib charts
embedded in the window: **top genres**, **ratings distribution**, and **movies by
decade**, alongside totals such as average rating given and most-watched genre.

---

## 5. Data Persistence

A single SQLite database (`data_store/moviematch.db`) holds four tables:

- `movies` — a cache of movie metadata, so favourites/analytics work offline
- `favorites` — saved movies
- `ratings` — the user's 1–5 star ratings (constrained at the database level)
- `history` — a log of viewed movies

Movie-specific tables reference `movies(movie_id)` as a foreign key, avoiding
duplicated data. All writes use parameterised SQL statements, protecting against
SQL injection and malformed input.

---

## 6. Testing and Quality

A suite of **offline unit tests** (`tests/test_core.py`, run with
`python -m unittest`) covers the model, storage, recommender and analytics
layers — without needing the network or a display. Tests verify, for example,
that ratings are validated (1–5 only), that recommendations prefer genre
overlap and exclude already-seen films, and that the analytics correctly
aggregate genres, decades and average ratings.

Because the logic layers are kept free of GUI code, they can be tested in
isolation, which is a direct benefit of the layered architecture.

---

## 7. How to Run

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt

# Add a free TMDB API key:
#   copy .env.example to .env and paste your key

python main.py
```

A free API key is obtained from the TMDB website (Settings → API). The
application launches even without one, with online features disabled.

---

## 8. Challenges and Future Work

**Challenges addressed**

- **Keeping the UI responsive** while making network calls — solved with a
  background-thread helper that marshals results back to the main thread.
- **Displaying JPEG posters in Tkinter**, which natively supports only a few
  image formats — solved with Pillow, taking care to create Tk image objects on
  the main thread only.
- **Making recommendations explainable** rather than opaque — solved by
  reporting the shared features behind every suggestion.

**Possible extensions**

- Add a lightweight collaborative-filtering layer ("users who liked X…")
- Support multiple user profiles
- Export the analytics charts to an image or PDF report
- Cache search results to reduce repeated API calls

---

## 9. Conclusion

MovieMatch fulfils all six required capabilities in a clean, modular and
well-tested application. It combines a real-world web API, local persistence, an
explainable recommendation algorithm and embedded data visualisation behind a
polished, responsive Tkinter interface — demonstrating practical application of
core Python programming concepts: object-oriented design, modular architecture,
data handling, concurrency and GUI development.
