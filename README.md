# Books scraper: a scheduled, polite web-scraping pipeline

<!-- After you push to GitHub, swap YOURNAME/REPO and the badge goes live. -->
![CI](https://github.com/YOURNAME/REPO/actions/workflows/ci.yml/badge.svg)

Scrapes the **books.toscrape.com** catalogue across all its pages, cleans and
de-duplicates the records, and loads them **idempotently** into a database. It runs
on a nightly **GitHub Actions** schedule and identifies itself, rate-limits, retries
politely, and respects `robots.txt`. The parsers are unit-tested against a **saved
HTML fixture**, so the test suite is fast, offline, and never hammers the site.

> books.toscrape.com is a sandbox built for scraping practice, scraping it is
> explicitly fine. Treat every other site with the same care: identify yourself,
> rate-limit, retry politely, and respect `robots.txt`.

## What it does

```
https://books.toscrape.com/catalogue/page-1.html
        │  FETCH (requests; user-agent, rate-limit, retries, robots.txt)   scraper/fetch.py
        ▼
   parse each book: title, price, rating, in-stock, url                     scraper/parse.py
        │  follow the "next" link → repeat for every page (pagination)
        ▼
   clean "£51.77"→51.77, "Three"→3; de-duplicate on url (pandas)            scraper/pipeline.py
        │  LOAD (idempotent upsert on url)                                  scraper/store.py
        ▼
   data/books.db (SQLite)  +  data/books.csv
```

## Run it locally

You're on Windows, so these are PowerShell commands.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # if blocked: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
pip install -r requirements.txt

# 1) run the tests (offline, they use the saved fixture, no network):
pytest

# 2) do a small real scrape (first 2 pages, polite 1.5s delay):
python -m scraper.pipeline --max-pages 2 --delay 1.5

# 3) scrape the whole catalogue (~50 pages, 1000 books; takes a couple of minutes
#    because we pause politely between requests):
python -m scraper.pipeline

# inspect the result
python -c "import pandas as pd; print(pd.read_csv('data/books.csv').head())"
```

To refresh the test fixture after the site's markup changes:

```powershell
python scripts\save_fixture.py
```

## Layout

```
├── scraper/
│   ├── parse.py        PURE parsing/cleaning functions (unit-tested, no network)
│   ├── fetch.py        polite fetching: user-agent, rate limit, retries, robots.txt
│   ├── store.py        idempotent upsert into SQLite (keyed on the book url)
│   └── pipeline.py     crawl pagination -> parse -> clean/dedupe -> store
├── tests/
│   ├── fixtures/listing_page.html   a real saved page; tests parse THIS, not the site
│   ├── test_parse.py   parser correctness against the fixture
│   └── test_store.py   the idempotency test (load twice -> same row count)
├── scripts/
│   ├── save_fixture.py refresh the saved page (the only script that hits the network)
│   └── ...
├── data/               books.csv (committed) + books.db (git-ignored)
├── .github/workflows/
│   ├── ci.yml          test parsers on every PR (offline)
│   └── scrape.yml      the nightly scheduled scrape (commits refreshed data)
├── requirements.txt    pinned dependencies
└── .env.example        template for secrets (real .env is git-ignored)
```

## Why tests use a saved fixture instead of the live site

Tests that fetch the live site are slow, flaky (network!), and hit the target on
every run, effectively DOSing it with your own CI. So we save one real page to
`tests/fixtures/` and parse *that*. The suite stays fast and offline, but still
catches the failure that actually happens in production: the site changes its HTML
and a selector breaks. When that happens, run `scripts/save_fixture.py`, watch the
test go red, fix the selector, watch it go green.

## Going to cloud Postgres (later)

This demo uses local SQLite so it runs with zero setup. To store in cloud Postgres
(e.g. a free Neon database), point a `DB_URL` at it and adapt `store.py`'s upsert to
Postgres' `INSERT ... ON CONFLICT (url) DO UPDATE`. The pattern is identical; only the
driver and connection string change. See `HOSTING.md`.

## Deploying / scheduling

See **`HOSTING.md`**: push to GitHub, turn on Actions, watch the nightly scrape
run, enable it to commit data back, add the status badge, and (optionally) wire up
Neon Postgres.
