"""Refresh the test fixture: download one real listing page and save it.

Run this when the site's HTML changes and your parser tests start failing — it
re-captures the page so your tests run against current markup. This is the ONE script
that deliberately hits the network; the tests themselves never do.

Run:  python scripts/save_fixture.py
"""
from pathlib import Path

from scraper.fetch import PoliteFetcher

URL = "https://books.toscrape.com/catalogue/page-1.html"
OUT = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "listing_page.html"


def main() -> None:
    html = PoliteFetcher(delay=0).get(URL)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"Saved {len(html)} chars from {URL} -> {OUT}")


if __name__ == "__main__":
    main()
