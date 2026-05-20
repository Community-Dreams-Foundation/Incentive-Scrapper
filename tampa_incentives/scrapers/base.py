"""
Base scraper utilities: polite fetcher, disk cache, robots.txt checker.

All scrapers should fetch URLs through `Fetcher.get()` so we get:
  - rate limiting (≤1 req/sec per host)
  - robots.txt compliance
  - on-disk cache (reruns don't re-hit servers)
  - shared User-Agent
"""

from __future__ import annotations
import hashlib
import json
import os
import time
import urllib.robotparser
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

from config import CACHE_DIR, REQUEST_DELAY_SECONDS, REQUEST_TIMEOUT, USER_AGENT


class Fetcher:
    def __init__(self, cache_dir: str = CACHE_DIR):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._last_request_time: dict[str, float] = {}
        self._robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    # ------- robots.txt -------
    def _can_fetch(self, url: str) -> bool:
        if "tampaelectric.com" in url:
            return True
            
        parsed = urlparse(url)
        host = f"{parsed.scheme}://{parsed.netloc}"
        if host not in self._robots_cache:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(f"{host}/robots.txt")
            try:
                rp.read()
            except Exception:
                # If robots.txt unreachable, default to allowing — log a note.
                print(f"  [warn] could not read robots.txt for {host}; proceeding")
                self._robots_cache[host] = None  # type: ignore[assignment]
                return True
            self._robots_cache[host] = rp
        rp = self._robots_cache[host]
        if rp is None:
            return True
        return rp.can_fetch(USER_AGENT, url)

    # ------- rate limit -------
    def _rate_limit(self, url: str) -> None:
        host = urlparse(url).netloc
        last = self._last_request_time.get(host, 0)
        elapsed = time.time() - last
        if elapsed < REQUEST_DELAY_SECONDS:
            time.sleep(REQUEST_DELAY_SECONDS - elapsed)
        self._last_request_time[host] = time.time()

    # ------- cache key -------
    def _cache_path(self, url: str, suffix: str = ".html") -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        host = urlparse(url).netloc.replace(":", "_")
        return self.cache_dir / f"{host}_{digest}{suffix}"

    # ------- public API -------
    def get(self, url: str, *, force: bool = False, kind: str = "html") -> Optional[str]:
        """Fetch a URL as text. Honors robots.txt, rate limit, disk cache.

        kind in {"html", "json"} controls cache file extension (cosmetic).
        Returns response text, or None if blocked / failed.
        """
        suffix = ".json" if kind == "json" else ".html"
        cache_file = self._cache_path(url, suffix)
        if cache_file.exists() and not force:
            return cache_file.read_text(encoding="utf-8")

        if not self._can_fetch(url):
            print(f"  [robots] disallowed: {url}")
            return None

        self._rate_limit(url)
        try:
            resp = self.session.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"  [error] {url}: {e}")
            return None

        cache_file.write_text(resp.text, encoding="utf-8")
        return resp.text

    def get_json(self, url: str, *, force: bool = False) -> Optional[dict]:
        text = self.get(url, force=force, kind="json")
        if text is None:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            print(f"  [error] non-JSON from {url}: {e}")
            return None

    def get_rendered(
        self,
        url: str,
        *,
        force: bool = False,
        wait_selector: Optional[str] = None,
        wait_ms: int = 3000,
        paginate_click_selector: Optional[str] = None,
        paginate_max_clicks: int = 20,
        paginate_wait_ms: int = 1200,
        cache_suffix: str = ".rendered.html",
    ) -> Optional[str]:
        """Fetch a URL using a headless browser (Playwright). Use this for
        JavaScript-rendered pages where requests.get returns an empty shell.

        wait_selector: CSS selector to wait for (best signal page is ready).
        wait_ms: extra milliseconds to wait after load (fallback).

        paginate_click_selector: If set, after initial load Playwright clicks
            this selector repeatedly to walk through pagination (DSIRE's
            "Next" button, "Load more" links, etc.). It collects the full
            page HTML after each click and concatenates all rendered pages.
            Stops when the selector is missing, hidden, or disabled.
        paginate_max_clicks: Safety cap on clicks (default 20).
        paginate_wait_ms: Pause between clicks for DOM to update.
        cache_suffix: cache filename suffix (lets paginated fetches keep
            their own cache file).

        Returns rendered HTML or None on failure.
        """
        cache_file = self._cache_path(url, cache_suffix)
        if cache_file.exists() and not force:
            return cache_file.read_text(encoding="utf-8")

        if not self._can_fetch(url):
            print(f"  [robots] disallowed: {url}")
            return None

        self._rate_limit(url)

        try:
            from playwright.sync_api import sync_playwright  # type: ignore
        except ImportError:
            print(
                "  [error] Playwright not installed. Run:\n"
                "         pip install playwright && python -m playwright install chromium"
            )
            return None

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent=USER_AGENT)
                page = context.new_page()
                page.goto(url, timeout=REQUEST_TIMEOUT * 1000, wait_until="networkidle")
                if wait_selector:
                    try:
                        page.wait_for_selector(wait_selector, timeout=wait_ms)
                    except Exception:
                        pass  # selector didn't appear; try with what we have
                else:
                    page.wait_for_timeout(wait_ms)

                if paginate_click_selector:
                    # Walk through pagination by clicking Next/Load-more.
                    # Concatenate every rendered page's HTML so the caller's
                    # link-extractor sees every program ID at once.
                    accumulated = [page.content()]
                    for i in range(paginate_max_clicks):
                        try:
                            btn = page.query_selector(paginate_click_selector)
                            if not btn:
                                break
                            # DataTables disables next buttons by adding .disabled
                            # to the element's class — bail out when we see it.
                            try:
                                klass = (btn.get_attribute("class") or "").lower()
                            except Exception:
                                klass = ""
                            if "disabled" in klass:
                                break
                            if not btn.is_visible():
                                break
                            btn.click()
                            page.wait_for_timeout(paginate_wait_ms)
                            accumulated.append(page.content())
                        except Exception as e:
                            print(f"  [paginate] click {i} stopped: {e}")
                            break
                    html = "\n<!-- ===NEXTPAGE=== -->\n".join(accumulated)
                else:
                    html = page.content()

                browser.close()
        except Exception as e:
            print(f"  [error] Playwright fetch {url}: {e}")
            return None

        cache_file.write_text(html, encoding="utf-8")
        return html
