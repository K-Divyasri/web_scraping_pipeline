"""Tests for the idempotent database load.

The headline test is idempotency: scrape the same books twice (as the nightly
schedule will), and the row count must NOT grow. That's the property that stops a
scheduled scraper from quietly doubling its dataset every run.
"""
from pathlib import Path

import sqlite3

from scraper.store import upsert_books

SAMPLE = [
    {"url": "https://x/1", "title": "Book One", "price_gbp": 10.0, "rating": 3, "in_stock": True},
    {"url": "https://x/2", "title": "Book Two", "price_gbp": 20.0, "rating": 5, "in_stock": False},
]


def test_upsert_inserts_rows(tmp_path: Path):
    db = tmp_path / "books.db"
    total = upsert_books(SAMPLE, db, scraped_at="2026-01-01T00:00:00+00:00")
    assert total == 2


def test_upsert_is_idempotent(tmp_path: Path):
    """Load the same two books twice -> still 2 rows, not 4."""
    db = tmp_path / "books.db"
    first = upsert_books(SAMPLE, db, scraped_at="2026-01-01T00:00:00+00:00")
    second = upsert_books(SAMPLE, db, scraped_at="2026-01-02T00:00:00+00:00")
    assert first == second == 2


def test_upsert_updates_changed_fields(tmp_path: Path):
    """If a book's price changes, the existing row is UPDATED, not duplicated."""
    db = tmp_path / "books.db"
    upsert_books(SAMPLE, db, scraped_at="2026-01-01T00:00:00+00:00")

    changed = [{**SAMPLE[0], "price_gbp": 99.99}]
    total = upsert_books(changed, db, scraped_at="2026-01-02T00:00:00+00:00")
    assert total == 2  # still two distinct books

    con = sqlite3.connect(str(db))
    price = con.execute("SELECT price_gbp FROM books WHERE url = ?", (SAMPLE[0]["url"],)).fetchone()[0]
    con.close()
    assert price == 99.99  # the row was updated in place
