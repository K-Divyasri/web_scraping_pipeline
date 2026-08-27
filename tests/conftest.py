"""Shared pytest fixtures.

The key idea: tests parse a SAVED copy of a real page (tests/fixtures/listing_page.html),
not the live site. That makes the suite fast, deterministic, offline, and polite —
yet it still catches the real failure mode: "the site changed its HTML and my parser
broke." When that happens you refresh the fixture (scripts/save_fixture.py) and watch
the test go red, then fix the selector.
"""
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "listing_page.html"
# The URL the fixture was captured from — parsers need it to resolve relative links.
FIXTURE_URL = "https://books.toscrape.com/catalogue/page-1.html"


@pytest.fixture
def listing_html() -> str:
    return FIXTURE.read_text(encoding="utf-8")


@pytest.fixture
def fixture_url() -> str:
    return FIXTURE_URL
