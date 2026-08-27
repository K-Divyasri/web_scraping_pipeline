"""Tests for the pure parsing functions, against a saved HTML fixture (offline).

Each test maps to a real failure it would catch. Run with:  pytest
"""
import pytest

from scraper.parse import clean_price, find_next_url, parse_listing, rating_word_to_int


# -- the small string cleaners -------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("£51.77", 51.77),
        ("Â£51.77", 51.77),    # the mojibake form the site actually serves
        ("13.00", 13.00),
        ("£9", 9.0),
    ],
)
def test_clean_price(raw, expected):
    """Catches: prices left as strings, or a currency-symbol/encoding breaking float()."""
    assert clean_price(raw) == expected


def test_clean_price_raises_on_garbage():
    with pytest.raises(ValueError):
        clean_price("no number here")


@pytest.mark.parametrize(
    "cls,expected",
    [("star-rating Three", 3), ("star-rating One", 1), ("star-rating Five", 5)],
)
def test_rating_word_to_int(cls, expected):
    """Catches: the rating (stored only as a word in a CSS class) not being parsed."""
    assert rating_word_to_int(cls) == expected


def test_rating_word_raises_on_unknown():
    with pytest.raises(ValueError):
        rating_word_to_int("star-rating Zero")


# -- the page parser, against the real saved page ------------------------------

def test_parse_listing_finds_twenty_books(listing_html, fixture_url):
    """This listing layout shows 20 books per page. Catches a broken pod selector."""
    books = parse_listing(listing_html, fixture_url)
    assert len(books) == 20


def test_parsed_book_has_all_fields(listing_html, fixture_url):
    """Catches: a missing/renamed field downstream code (and the DB) expects."""
    book = parse_listing(listing_html, fixture_url)[0]
    assert set(book) == {"title", "price_gbp", "rating", "in_stock", "url"}
    assert book["title"]                       # non-empty
    assert isinstance(book["price_gbp"], float)
    assert 1 <= book["rating"] <= 5
    assert isinstance(book["in_stock"], bool)
    assert book["url"].startswith("https://")  # relative link was made absolute


def test_first_book_values(listing_html, fixture_url):
    """A concrete known-good row. Catches a subtle selector/cleaning regression."""
    book = parse_listing(listing_html, fixture_url)[0]
    assert book["title"] == "A Light in the Attic"
    assert book["price_gbp"] == 51.77
    assert book["rating"] == 3
    assert book["in_stock"] is True


def test_find_next_url(listing_html, fixture_url):
    """Page 1 must point to page 2 (absolute URL). Catches broken pagination."""
    nxt = find_next_url(listing_html, fixture_url)
    assert nxt == "https://books.toscrape.com/catalogue/page-2.html"


def test_no_next_on_last_page(fixture_url):
    """A page with no 'next' link returns None — that's how the crawl knows to stop."""
    html = "<html><body><ul class='pager'><li class='previous'><a href='x'>prev</a></li></ul></body></html>"
    assert find_next_url(html, fixture_url) is None
