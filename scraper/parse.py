"""The PARSE stage — pure functions only.

"Pure" means: HTML or a string goes in, clean data comes out. No network, no files,
no database, no clock. That property is why these are trivial to test: a test hands
in a saved HTML fixture and checks the records that come back. Every public function
here has a matching test in ../tests/test_parse.py.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

# Maps the rating word baked into the CSS class (e.g. "star-rating Three") to a number.
_WORD_TO_NUM = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}


def clean_price(raw: str) -> float:
    """'£51.77' (or the mojibake 'Â£51.77') -> 51.77.

    The site serves the £ sign with an encoding that often arrives as junk bytes, so
    we don't try to strip a specific currency symbol — we just pull the first number
    out with a regex. Robust beats clever.
    """
    match = re.search(r"\d+(?:\.\d+)?", raw)
    if not match:
        raise ValueError(f"no number found in price string: {raw!r}")
    return float(match.group())


def rating_word_to_int(class_value: str) -> int:
    """'star-rating Three' -> 3. Raises if the word isn't a known rating."""
    for word, num in _WORD_TO_NUM.items():
        if word in class_value:
            return num
    raise ValueError(f"no rating word found in: {class_value!r}")


def parse_listing(html: str, page_url: str) -> list[dict]:
    """Parse one catalogue listing page into a list of book records.

    page_url is the URL the HTML came from; we need it to turn the relative book
    links ('a-light-in-the-attic_1000/index.html') into absolute URLs.
    """
    soup = BeautifulSoup(html, "lxml")
    books: list[dict] = []

    for pod in soup.select("article.product_pod"):
        link = pod.select_one("h3 a")
        title = link["title"].strip()
        url = urljoin(page_url, link["href"])

        price = clean_price(pod.select_one("p.price_color").get_text())

        rating_p = pod.select_one("p.star-rating")
        rating = rating_word_to_int(" ".join(rating_p.get("class", [])))

        availability = pod.select_one("p.instock.availability").get_text(strip=True)
        in_stock = "in stock" in availability.lower()

        books.append(
            {
                "title": title,
                "price_gbp": price,
                "rating": rating,
                "in_stock": in_stock,
                "url": url,
            }
        )

    return books


def find_next_url(html: str, page_url: str) -> str | None:
    """Return the absolute URL of the 'next' page, or None if this is the last page.

    Pagination on this site is a <li class="next"><a href="page-2.html">. We follow
    that link until it's gone — that's how you crawl every page.
    """
    soup = BeautifulSoup(html, "lxml")
    next_link = soup.select_one("li.next a")
    if next_link is None:
        return None
    return urljoin(page_url, next_link["href"])
