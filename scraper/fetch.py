"""The FETCH stage — the polite network layer.

Everything that makes a scraper a good internet citizen lives here:
  - a descriptive, honest User-Agent (says who we are, with a contact)
  - a rate limit (a deliberate pause between requests)
  - retries with exponential back-off (handle blips and 429/503 without giving up)
  - a robots.txt check (respect what the site asks bots not to crawl)

None of this is about the data. It's about not being the reason a site bans scrapers.
"""
from __future__ import annotations

import logging
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests

log = logging.getLogger("scraper.fetch")

# Honest user-agent: a name, a version, and a way to contact you. Change the email.
USER_AGENT = "BookBot/1.0 (+https://example.com/bookbot; learning@example.com)"

# Status codes worth retrying: transient server/throttling errors.
RETRY_STATUS = {429, 500, 502, 503, 504}


class PoliteFetcher:
    """A small wrapper around a requests.Session that paces and retries itself."""

    def __init__(self, delay: float = 1.0, max_retries: int = 3, timeout: float = 20.0):
        self.delay = delay          # seconds to wait between successful requests
        self.max_retries = max_retries
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self._robots: dict[str, RobotFileParser] = {}

    # -- robots.txt -----------------------------------------------------------
    def allowed(self, url: str) -> bool:
        """True if this site's robots.txt permits our user-agent to fetch url.

        We cache one parser per host so we only download robots.txt once.
        """
        parts = urlparse(url)
        host = f"{parts.scheme}://{parts.netloc}"
        if host not in self._robots:
            rp = RobotFileParser()
            rp.set_url(f"{host}/robots.txt")
            try:
                rp.read()
            except Exception as exc:  # if robots.txt can't be read, fail safe = allow
                log.warning("could not read robots.txt for %s: %s", host, exc)
            self._robots[host] = rp
        return self._robots[host].can_fetch(USER_AGENT, url)

    # -- fetching -------------------------------------------------------------
    def get(self, url: str) -> str:
        """Fetch url and return its text, retrying transient failures with back-off.

        Raises if robots.txt disallows the URL, or if all retries fail.
        """
        if not self.allowed(url):
            raise PermissionError(f"robots.txt disallows fetching {url}")

        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                resp = self.session.get(url, timeout=self.timeout)
                if resp.status_code in RETRY_STATUS:
                    raise requests.HTTPError(f"retryable status {resp.status_code}")
                resp.raise_for_status()
                time.sleep(self.delay)          # be polite AFTER a success too
                return resp.text
            except Exception as exc:
                last_error = exc
                backoff = self.delay * (2 ** (attempt - 1))   # 1s, 2s, 4s, ...
                log.warning("fetch %s failed (attempt %d/%d): %s; backing off %.1fs",
                            url, attempt, self.max_retries, exc, backoff)
                time.sleep(backoff)

        raise RuntimeError(f"failed to fetch {url} after {self.max_retries} attempts") from last_error
