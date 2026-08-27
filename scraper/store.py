"""The LOAD stage — an idempotent upsert into SQLite.

Idempotent = running the load again gives the same result as once, with no duplicate
rows. A scheduled scraper re-scrapes the same books every night, so a blind append
would double the data each run. We avoid that with an UPSERT keyed on the book's URL:
update the row if that URL already exists, insert it if it doesn't.

SQLite's `INSERT ... ON CONFLICT(url) DO UPDATE` does exactly that. There's a test
(test_store.py) that loads twice and asserts the row count doesn't change.
"""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

log = logging.getLogger("scraper.store")

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS books (
    url         TEXT PRIMARY KEY,   -- the stable key we upsert on
    title       TEXT NOT NULL,
    price_gbp   REAL NOT NULL,
    rating      INTEGER NOT NULL,
    in_stock    INTEGER NOT NULL,   -- SQLite stores booleans as 0/1
    scraped_at  TEXT NOT NULL
)
"""

UPSERT_SQL = """
INSERT INTO books (url, title, price_gbp, rating, in_stock, scraped_at)
VALUES (:url, :title, :price_gbp, :rating, :in_stock, :scraped_at)
ON CONFLICT(url) DO UPDATE SET
    title      = excluded.title,
    price_gbp  = excluded.price_gbp,
    rating     = excluded.rating,
    in_stock   = excluded.in_stock,
    scraped_at = excluded.scraped_at
"""


def upsert_books(records: list[dict], db_path: str | Path, scraped_at: str) -> int:
    """Upsert records into the books table. Returns the total row count afterwards.

    Each record needs: url, title, price_gbp, rating, in_stock. `scraped_at` (an ISO
    timestamp string) is stamped onto every row by the caller so the function stays
    free of the clock and therefore easy to test deterministically.
    """
    con = sqlite3.connect(str(db_path))
    try:
        con.execute(CREATE_SQL)
        rows = [
            {
                "url": r["url"],
                "title": r["title"],
                "price_gbp": float(r["price_gbp"]),
                "rating": int(r["rating"]),
                "in_stock": 1 if r["in_stock"] else 0,
                "scraped_at": scraped_at,
            }
            for r in records
        ]
        con.executemany(UPSERT_SQL, rows)
        con.commit()
        (total,) = con.execute("SELECT COUNT(*) FROM books").fetchone()
    finally:
        con.close()
    log.info("upserted %d records; table now holds %d rows", len(records), total)
    return int(total)
