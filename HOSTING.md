# Hosting & scheduling this project (all free)

This takes you from "a scraper on my laptop" to "a scraper that GitHub runs for me
every night, for free, committing fresh data each time." Every step costs £0.

You host the **`build/`** project. The `knowledge/` folder is private study material
and doesn't need hosting.

> Prerequisite: a free GitHub account and git installed (you used git in notebook 02).

---

## Step 1 — Make the build folder its own git repo

A portfolio repo should contain just the project, so we init git inside `build/`.

```powershell
cd C:\Users\divya\Downloads\learning\data_engineer\17_web_scraping_pipeline\build

git init
git add .
git status        # sanity-check: you should NOT see .env, .venv, or data/books.db
                  # (they're git-ignored). data/books.csv SHOULD be staged.
git commit -m "Books scraper: polite scheduled web-scraping pipeline"
```

> Why the `git status` check: the most common junior mistake is committing a secret
> or a huge venv. `.gitignore` already prevents it — this is you verifying.

---

## Step 2 — Create the repo on GitHub and push

1. https://github.com/new
2. Name it e.g. `books-scraper-pipeline`. **Leave it empty** (no README/.gitignore).
3. Create, then:

```powershell
git remote add origin https://github.com/YOURNAME/books-scraper-pipeline.git
git branch -M main
git push -u origin main
```

---

## Step 3 — Watch CI run (the parser tests)

`ci.yml` runs on every push/PR. It installs deps and runs `pytest` against the saved
HTML fixture — **offline**, so it never touches the live site.

1. Repo → **Actions** tab → click the **CI** run → the `test` job.
2. Watch it install and run 17 tests green.

If it's red, click the failed step and read the log. The usual first-time cause is a
file not committed (e.g. the fixture) — confirm `tests/fixtures/listing_page.html` is
in the repo.

---

## Step 4 — Turn on the nightly scrape (the actual pipeline)

`scrape.yml` is the heart of this project: a scheduled (`cron`) job that scrapes the
live catalogue and commits the refreshed `data/books.csv` back to the repo.

### Let Actions write to your repo
The job needs permission to push the updated data:

1. Repo → **Settings** → **Actions** → **General**.
2. Scroll to **Workflow permissions** → choose **Read and write permissions** → Save.
   (The workflow also declares `permissions: contents: write`, but this repo-level
   setting must allow it.)

### Run it once by hand (don't wait until tonight)
1. Repo → **Actions** → **Nightly scrape** (left sidebar) → **Run workflow** button
   (this exists because the workflow declares `workflow_dispatch`).
2. Watch it scrape ~50 pages politely (a couple of minutes — the delays are
   deliberate), then commit `data: refresh scraped books (…)` if the data changed.
3. Refresh the repo's code tab → open `data/books.csv` → it's the freshly scraped
   1,000-row dataset, updated by a robot. That's a real, scheduled data pipeline.

From now on it also runs automatically at 06:00 UTC daily. Change the `cron` line in
`scrape.yml` to re-time it (the syntax is `minute hour day month weekday`).

> Note on GitHub's scheduler: scheduled workflows can be delayed at peak times, and
> GitHub disables schedules on repos with no activity for 60 days. For a portfolio
> that's fine; just push occasionally.

---

## Step 5 — Add the status badge

1. Open `build/README.md`; the first lines already have:
   ```markdown
   ![CI](https://github.com/YOURNAME/REPO/actions/workflows/ci.yml/badge.svg)
   ```
2. Replace `YOURNAME/REPO` with your `username/repository`, commit, push.
3. A green **CI passing** badge appears at the top. (Actions → CI → ⋯ → *Create
   status badge* gives you the exact URL too.)

---

## Step 6 — (Optional) store the data in cloud Postgres (Neon)

Committing a CSV is great for a portfolio. To make it a "real" warehouse load:

1. Make a free Postgres database at https://neon.tech and copy its connection string.
2. Add it as a repo secret: **Settings → Secrets and variables → Actions → New
   repository secret**, name `DB_URL`.
3. Adapt `scraper/store.py` to use Postgres. The upsert is nearly identical:
   ```sql
   INSERT INTO books (url, title, price_gbp, rating, in_stock, scraped_at)
   VALUES (%(url)s, %(title)s, %(price_gbp)s, %(rating)s, %(in_stock)s, %(scraped_at)s)
   ON CONFLICT (url) DO UPDATE SET
       title = EXCLUDED.title, price_gbp = EXCLUDED.price_gbp,
       rating = EXCLUDED.rating, in_stock = EXCLUDED.in_stock,
       scraped_at = EXCLUDED.scraped_at;
   ```
   (Use `psycopg[binary]` or SQLAlchemy; read `DB_URL` from the environment.)
4. In `scrape.yml`, expose the secret to the scrape step:
   ```yaml
   - name: Scrape the catalogue
     run: python -m scraper.pipeline --delay 1.0
     env:
       DB_URL: ${{ secrets.DB_URL }}
   ```
Now the nightly job loads straight into cloud Postgres — same idempotent pattern,
different driver. That's a genuinely production-shaped pipeline.

---

## The scraping-ethics checklist (re-read before scraping any real site)

This demo targets a sandbox that welcomes scrapers. Before you ever point this code
at a real site, every time:

- [ ] Is there an **API or bulk dataset** I should use instead? Prefer it.
- [ ] Read the site's **`robots.txt`** and **Terms of Service**. Respect them.
- [ ] Set an **honest, contactable User-Agent** (edit it in `scraper/fetch.py`).
- [ ] **Rate-limit** — at least 1–3 seconds between requests; back off on 429/503.
- [ ] Am I touching **personal data**? If so, GDPR/CCPA apply — usually don't.
- [ ] Only take what you need; cache so you don't re-fetch.

Getting blocked is almost always a symptom of being impolite. Don't reach for proxies
and fake user-agents to force your way past a site that doesn't want you — that's the
point where you should reconsider whether you should be scraping it at all.

---

## Recap — what you now have hosted

- A public GitHub repo with a real, documented scraper.
- A green **CI badge** proving the parsers are tested (offline).
- A **nightly scheduled** scrape that **commits fresh data** by itself.
- (Optional) the same data flowing into **cloud Postgres** on Neon.

Every word of the resume line is now literally true of your repo: *"Built a scheduled
web-scraping pipeline with parsing, dedup, and database loading."*
