"""The pipeline — crawl pages, parse, clean/dedupe, store. Ties the stages together.

Run it:  python -m scraper.pipeline
         python -m scraper.pipeline --max-pages 3 --delay 1.5
"""
from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .fetch import PoliteFetcher
from .parse import find_next_url, parse_listing
from .store import upsert_books

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("scraper.pipeline")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
START_URL = "https://books.toscrape.com/catalogue/page-1.html"
DEFAULT_DB = PROJECT_ROOT / "data" / "books.db"
DEFAULT_CSV = PROJECT_ROOT / "data" / "books.csv"


def crawl(start_url: str, fetcher: PoliteFetcher, max_pages: int | None = None) -> list[dict]:
    """Follow 'next' links from start_url, parsing each page. Returns all records."""
    records: list[dict] = []
    url: str | None = start_url
    page = 0
    while url:
        page += 1
        log.info("fetching page %d: %s", page, url)
        html = fetcher.get(url)
        page_records = parse_listing(html, url)
        log.info("  parsed %d books", len(page_records))
        records.extend(page_records)
        if max_pages and page >= max_pages:
            log.info("reached max_pages=%d, stopping", max_pages)
            break
        url = find_next_url(html, url)
    return records


def clean_and_dedupe(records: list[dict]) -> pd.DataFrame:
    """Put records in a DataFrame, drop duplicate books (same URL), sort."""
    df = pd.DataFrame(records)
    before = len(df)
    df = df.drop_duplicates(subset=["url"], keep="last").reset_index(drop=True)
    log.info("deduped %d -> %d records", before, len(df))
    return df.sort_values("title").reset_index(drop=True)


def run(
    start_url: str = START_URL,
    db_path: Path = DEFAULT_DB,
    csv_path: Path = DEFAULT_CSV,
    delay: float = 1.0,
    max_pages: int | None = None,
) -> int:
    fetcher = PoliteFetcher(delay=delay)
    records = crawl(start_url, fetcher, max_pages=max_pages)
    df = clean_and_dedupe(records)

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    log.info("wrote %s", csv_path)

    scraped_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    total = upsert_books(df.to_dict("records"), db_path, scraped_at)
    log.info("done: %d books in %s", total, db_path)
    return total


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape books.toscrape.com into a database")
    parser.add_argument("--max-pages", type=int, default=None, help="limit pages (default: all)")
    parser.add_argument("--delay", type=float, default=1.0, help="seconds between requests")
    parser.add_argument("--db", default=str(DEFAULT_DB))
    parser.add_argument("--csv", default=str(DEFAULT_CSV))
    args = parser.parse_args()
    run(db_path=Path(args.db), csv_path=Path(args.csv), delay=args.delay, max_pages=args.max_pages)


if __name__ == "__main__":
    main()
