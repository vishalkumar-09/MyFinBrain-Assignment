"""
sources/rss_source.py
=====================
Generic RSS/Atom feed adapter built on feedparser.

This is both:
  1. A standalone adapter that can read any RSS feed URL.
  2. The base class for all source-specific adapters that consume RSS.

Source-specific adapters (e.g. TechCrunch, Inc42) subclass RSSSource and
override ``RSS_FEEDS`` and optionally ``_parse_entry`` to handle site-specific
metadata quirks.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Iterator, Optional
from email.utils import parsedate_to_datetime

import feedparser

from sources.base import Article, BaseSource, ExtractionStatus, canonicalize_url
from sources import registry
from config.settings import START_DATE, END_DATE, USER_AGENT, REQUEST_DELAY_SECONDS, REQUEST_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


def _parse_feed_date(entry: feedparser.FeedParserDict) -> Optional[datetime]:
    """
    Extract a timezone-aware datetime from an RSS entry.
    Tries multiple standard feedparser fields.
    """
    # feedparser parses most dates into a time.struct_time stored in *_parsed
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        struct = getattr(entry, attr, None)
        if struct:
            try:
                # time.struct_time → datetime (UTC)
                return datetime(*struct[:6], tzinfo=timezone.utc)
            except Exception:
                pass

    # Fallback: raw string fields
    for attr in ("published", "updated"):
        raw = getattr(entry, attr, None)
        if raw:
            try:
                return parsedate_to_datetime(raw)
            except Exception:
                pass
    return None


class RSSSource(BaseSource):
    """
    Generic RSS/Atom source adapter.

    Subclasses should override:
    - ``SOURCE_ID``  – unique source identifier
    - ``SOURCE_NAME`` – display name
    - ``RSS_FEEDS``  – list of feed URLs to poll
    """

    SOURCE_ID: str = "rss_generic"
    SOURCE_NAME: str = "Generic RSS"
    RSS_FEEDS: list[str] = []

    def __init__(
        self,
        start_date: date = START_DATE,
        end_date: date = END_DATE,
        rss_feeds: Optional[list[str]] = None,
        user_agent: str = USER_AGENT,
        request_delay: float = REQUEST_DELAY_SECONDS,
        timeout: int = REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        super().__init__(
            start_date=start_date,
            end_date=end_date,
            user_agent=user_agent,
            request_delay=request_delay,
            timeout=timeout,
        )
        # Feeds may be injected at instantiation (useful for tests)
        self._feeds: list[str] = rss_feeds if rss_feeds is not None else list(self.RSS_FEEDS)
        self._seen_urls: set[str] = set()

    # ------------------------------------------------------------------
    # Core discovery
    # ------------------------------------------------------------------

    def discover(self) -> Iterator[Article]:
        """Yield articles from every configured RSS feed."""
        if not self._feeds:
            self._logger.warning("%s: no RSS feeds configured", self.SOURCE_ID)
            return

        for feed_url in self._feeds:
            yield from self._process_feed(feed_url)

    def _process_feed(self, feed_url: str) -> Iterator[Article]:
        """Parse one RSS feed and yield Article objects."""
        self._logger.info("Fetching RSS feed: %s", feed_url)
        try:
            # feedparser can fetch the URL itself; use our session for headers
            resp = self._get(feed_url)
            if resp is None:
                self.health.articles_failed += 1
                return
            feed = feedparser.parse(resp.text)
        except Exception as exc:
            self._logger.error("Failed to parse feed %s: %s", feed_url, exc)
            self.health.record_error(f"Feed parse error {feed_url}: {exc}")
            return

        if feed.bozo and feed.bozo_exception:
            self._logger.debug(
                "Feed %s returned with bozo flag: %s", feed_url, feed.bozo_exception
            )

        for entry in feed.entries:
            try:
                article = self._parse_entry(entry, feed_url, feed)
                if article is None:
                    continue
                canonical = canonicalize_url(article.url)
                if canonical in self._seen_urls:
                    self._logger.debug("Duplicate URL skipped: %s", article.url)
                    continue
                self._seen_urls.add(canonical)
                yield article
            except Exception as exc:
                self._logger.warning("Error parsing entry from %s: %s", feed_url, exc)
                self.health.articles_failed += 1

    def _parse_entry(
        self,
        entry: feedparser.FeedParserDict,
        feed_url: str,
        feed: feedparser.FeedParserDict,
    ) -> Optional[Article]:
        """
        Convert a feedparser entry into an Article.
        Override in subclasses for source-specific behaviour.
        """
        url = getattr(entry, "link", None)
        if not url:
            return None

        title = getattr(entry, "title", "") or ""
        title = title.strip()
        if not title:
            return None

        summary = (
            getattr(entry, "summary", None)
            or getattr(entry, "description", None)
            or None
        )
        if summary:
            # Strip basic HTML from summaries
            from html.parser import HTMLParser

            class _Stripper(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self._parts: list[str] = []

                def handle_data(self, data: str):
                    self._parts.append(data)

                def get_text(self) -> str:
                    return " ".join(self._parts)

            stripper = _Stripper()
            stripper.feed(summary)
            summary = stripper.get_text().strip() or None

        author = getattr(entry, "author", None)
        published_at = _parse_feed_date(entry)

        return Article(
            url=url,
            title=title,
            source_id=self.SOURCE_ID,
            source_name=self.SOURCE_NAME,
            summary=summary,
            author=author,
            published_at=published_at,
            feed_url=feed_url,
            extraction_status=ExtractionStatus.PENDING,
        )

    # ------------------------------------------------------------------
    # Convenience: add feeds at runtime
    # ------------------------------------------------------------------

    def add_feed(self, url: str) -> None:
        if url not in self._feeds:
            self._feeds.append(url)
