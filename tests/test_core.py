"""Offline tests for MovieMatch's core logic (no network, no GUI).

Run with:  python -m unittest discover -s tests
"""

import tempfile
import unittest
from pathlib import Path

from moviematch.analytics.habits import build_report
from moviematch.data.storage import Storage
from moviematch.models import Movie
from moviematch.recommender.content_based import recommend


def make_movie(mid, title, genres, keywords=(), year=2000):
    return Movie(
        id=mid,
        title=title,
        release_date=f"{year}-01-01",
        genres=list(genres),
        keywords=list(keywords),
    )


class ModelTests(unittest.TestCase):
    def test_year_and_decade(self):
        m = make_movie(1, "X", ["Action"], year=1994)
        self.assertEqual(m.year, 1994)
        self.assertEqual(m.decade, "1990s")

    def test_round_trips_through_storage_dict(self):
        m = make_movie(1, "X", ["Action", "Sci-Fi"], ["space"])
        d = m.to_storage_dict()
        self.assertIn("Action", d["genres"])


class StorageTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Path(self._tmp.name) / "test.db"
        self.store = Storage(db_path=self.db)

    def tearDown(self):
        self.store.close()
        self._tmp.cleanup()

    def test_favorites_roundtrip(self):
        m = make_movie(10, "Fav", ["Drama"])
        self.store.add_favorite(m)
        self.assertTrue(self.store.is_favorite(10))
        self.assertEqual(len(self.store.list_favorites()), 1)
        self.store.remove_favorite(10)
        self.assertFalse(self.store.is_favorite(10))

    def test_rating_validation_and_storage(self):
        m = make_movie(11, "Rated", ["Comedy"])
        self.store.set_rating(m, 4)
        self.assertEqual(self.store.get_rating(11), 4)
        with self.assertRaises(ValueError):
            self.store.set_rating(m, 9)

    def test_history_logged(self):
        m = make_movie(12, "Seen", ["Horror"])
        self.store.log_view(m)
        self.store.log_view(m)
        self.assertEqual(len(self.store.list_history()), 2)


class RecommenderTests(unittest.TestCase):
    def test_prefers_genre_overlap(self):
        liked = [(make_movie(1, "Liked", ["Action", "Adventure"], ["hero"]), 5.0)]
        candidates = [
            make_movie(2, "Match", ["Action", "Adventure"], ["hero"]),
            make_movie(3, "NoMatch", ["Romance"], ["wedding"]),
        ]
        recs = recommend(liked, candidates)
        self.assertEqual(recs[0].movie.id, 2)
        self.assertTrue(all(r.movie.id != 3 for r in recs))  # zero overlap dropped

    def test_excludes_seen(self):
        liked = [(make_movie(1, "Liked", ["Action"]), 5.0)]
        candidates = [make_movie(1, "Liked", ["Action"]), make_movie(2, "New", ["Action"])]
        recs = recommend(liked, candidates, exclude_ids={1})
        self.assertEqual([r.movie.id for r in recs], [2])

    def test_reasons_explain_match(self):
        liked = [(make_movie(1, "L", ["Sci-Fi"], ["space"]), 5.0)]
        recs = recommend(liked, [make_movie(2, "C", ["Sci-Fi"], ["space"])])
        self.assertIn("Sci-Fi", recs[0].reasons)


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.store = Storage(db_path=Path(self._tmp.name) / "a.db")

    def tearDown(self):
        self.store.close()
        self._tmp.cleanup()

    def test_report_aggregates(self):
        self.store.add_favorite(make_movie(1, "A", ["Action"], year=1995))
        self.store.set_rating(make_movie(2, "B", ["Action", "Drama"], year=2005), 5)
        self.store.set_rating(make_movie(3, "C", ["Drama"], year=2005), 3)
        report = build_report(self.store)
        self.assertEqual(report.total_favorites, 1)
        self.assertEqual(report.total_rated, 2)
        self.assertEqual(report.average_rating, 4.0)
        self.assertEqual(report.top_genre, "Action")  # appears in 2 movies
        self.assertEqual(report.decade_counts["2000s"], 2)


if __name__ == "__main__":
    unittest.main()
