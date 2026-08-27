"""books_scraper — a polite, scheduled scraper for books.toscrape.com.

Modules are split by job, on purpose:
  parse.py     PURE functions: HTML/strings in, clean data out. No network.
               This is the easy-to-test heart of the scraper.
  fetch.py     the polite network layer: a session with a user-agent, a rate
               limit, retries with back-off, and a robots.txt check.
  store.py     the idempotent database load (upsert on the book URL).
  pipeline.py  ties it together: crawl pages -> parse -> clean -> store.

Keeping parse.py pure is what lets the tests run offline against saved HTML
fixtures — fast, deterministic, and without hammering the live site.
"""
from .parse import clean_price, rating_word_to_int, parse_listing, find_next_url

__all__ = ["clean_price", "rating_word_to_int", "parse_listing", "find_next_url"]
