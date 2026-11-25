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

import html as html_lib
import logging
import re
from datetime import date, datetime, timezone
from typing import Iterator, Optional
from email.utils import parsedate_to_datetime

import feedparser
from bs4 import BeautifulSoup
from dateutil import parser as dateutil_parser

from sources.base import Article, BaseSource, ExtractionStatus, canonicalize_url
from sources import registry
from config.settings import START_DATE, END_DATE, USER_AGENT, REQUEST_DELAY_SECONDS, REQUEST_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Title-level funding signal & noise filters
# ---------------------------------------------------------------------------
_FUNDING_TITLE_KEYWORDS = {
    "raise", "raises", "raised", "raising",
    "fund", "funded", "funding", "fundraise",
    "secures", "secured", "securing",
    "bags", "bagged",
    "lands", "landed",
    "closes", "closed", "closing",
    "invest", "investment", "investor",
    "backs", "backed", "backing",
    "capital", "financing", "equity",
    "series a", "series b", "series c", "series d", "series e", "series f", "series g",
    "seed round", "seed funding", "pre-seed", "angel round",
    "growth round", "venture", "vc",
    "million", "billion", "crore", "mn", "cr",
    "gets", "get", "garners", "nets",
    "pre-ipo", "unicorn", "valuation",
}

_NOISE_TITLE_RE = re.compile(
    r"(?:"
    r"\bweekly\s+(?:funding|notable\s+startup\s+funding|vc\s+funding)"
    r"|\bdaily\s+funding\s+report\b"
    r"|\bindian\s+startups?\s+raised\b"
    r"|\bstartups?\s+raised\s+[\$₹\d]"
    r"|\b(?:fintech|wealthtech|vc|startup)\s+(?:funding|investment|venture\s+capital|deal\s+activity)\s+(?:roundup|roars|tops|soars|surged|projected|grew|hit|in\s+(?:july|august|september|october|november|q\d))\b"
    r"|\b(?:doubled\s+yoy\s+in\s+q\d|deal\s+activity\s+projected\s+to|may\s+have\s+sold\s+.*portfolio)\b"
    r"|\breal\s+estate\s+debt\s+fund\b|\bdebt\s+vintage\b|\bfund\s+launch\b|\bai-driven\s+hedge\s+fund\s+raises\b"
    r"|\b(?:top\s+largest|largest\s+.*funding)\b"
    r"|\b(?:new\s+york|us|indian|global)\s+venture\s+capital\s+(?:in\s+)?(?:january|february|march|april|may|june|july|august|september|october|november|december)\b"
    r"|\bfintech\s+market\s+roars\b"
    r"|\braised\s+(?:across|in\s+this\s+week|\$[\d\.]+[mb]n?\s+across)\b"
    r"|\bacquires\b|\bacquisition\b|\bto\s+acquire\b|\bmerges\s+with\b|\bto\s+sell\b|\bsells\s+(?:stake|[\d\.]+%\s+stake)\b|\bblock\s+deal\b"
    r"|\b(?:q[1-4]|h[12]|fy\d{2})\b.{0,25}\b(?:profit|loss|revenue|results|earnings)\b"
    r"|\blayoffs?\b|\bshutdown\b|\binsolvency\b|\bfraudulent\b"
    r"|\b(?:files?\s+drhp|drhp\s+with|ipo-bound)\b"
    r"|\bmobility:\s+.*robotaxis\b"
    r"|\b(?:unveils\s+.*(?:platform|fund)|extends\s+ai\s+platform|targets\s+.*data\s+problem|selects\s+.*for\s+private\s+assets)\b"
    r"|\bto\s+invest\s+in\s+wealthtech\s+platform\b"
    r"|\braises\s+\$?\d+.*?\bfor\s+top\s+private\s+equity\s+pool\b"
    r"|\braises\s+(?:rs\.?|₹)?[\d,\.]+\s*(?:cr|crore)?\s+(?:through|via)\s+(?:its\s+)?(?:second\s+)?credit\s+strategy\b"
    r"|\bcommits?\s+(?:rs\.?|₹|\$|€|£)?[\d,\.]+"
    r"|\blaunches?\s+(?:rs|₹|\$|€|£|inr|usd)?[\d,\.]*\s*(?:cr|crore|million|mn|m|bn|billion)?\s*(?:fund|debut\s+fund|fund\s+[ivx0-9]+|special\s+situations|deeptech\s+fund|consumer\s+fund)\b"
    r"|\bcloses?\s+(?:fund\s+[ivx0-9]+|debut\s+fund|second\s+fund|third\s+fund|fourth\s+fund|sixth\s+fund|fund\s+[ivx0-9]+|[\$₹]?[\d\.,]+\s*(?:mn|cr|million|billion|crore)?\s*(?:debut\s+|venture\s+|credit\s+|growth\s+)?fund\b)"
    r"|\bfirst\s+close\s+(?:of|for)\s+(?:its\s+|a\s+)?(?:[\$₹]?[\d\.,]+|second|maiden|special|private)"
    r"|\bfinal\s+close\s+(?:of|for)\b"
    r"|\bsenior\s+secured\s+notes\s+offering\b|\bnotes\s+offering\b|\brefinancing\s+for\b"
    r"|\bloan\s+on\b.{0,30}\b(?:property|towers|apartments|housing)\b"
    r")",
    re.IGNORECASE,
)


def _title_has_funding_signal(title: str) -> bool:
    """Return True if the article title signals a genuine funding event and is not a roundup/M&A/earnings piece."""
    lower = title.lower()
    if _NOISE_TITLE_RE.search(lower):
        return False
    return any(kw in lower for kw in _FUNDING_TITLE_KEYWORDS)


def _extract_wp_body_text(rendered_html: str) -> str:
    """Extract clean article paragraphs from WordPress HTML content."""
    if not rendered_html:
        return ""
    soup = BeautifulSoup(rendered_html, "html.parser")
    paras = [p.get_text(" ", strip=True) for p in soup.find_all(["p", "li"]) if p.get_text(strip=True)]
    if paras:
        return "\n\n".join(paras)
    return soup.get_text(" ", strip=True)


_SITEMAP_TARGET_SLUG_RE = re.compile(
    r"(?:^|[-/])(?:wealth|wealthtech|asset-management|portfolio|advis|bond|private-market|"
    r"private-credit|private-equity|pre-ipo|brokerage|broker|trading|investment-platform|"
    r"investment-app|fixed-income|fractional|alternative|family-office|hedge-fund|"
    r"ionic-wealth|powerup|nexedge|veriqus|centricity|stable-money|finny|finnyclub|zomint|"
    r"mochatrade|tradl|definedge|sahi|smallcase|dezerv|dhan|jiraaf|grip|wint|"
    r"scripbox|indmoney|fincart)(?:$|[-/\d])",
    re.IGNORECASE,
)

_SITEMAP_FUNDING_SLUG_RE = re.compile(
    r"(?:raise|secur|bag|land|net|series|seed|angel|funding|round|investment|capital)",
    re.IGNORECASE,
)

_SITEMAP_SKIP_SLUG_RE = re.compile(
    r"(?:weekly-funding|roundup|fintrackr|block-deal|sells-|stake-in|acquires|"
    r"acquisition|launches-rs|closes-rs|profit|revenue|loss|report|vc-funding)",
    re.IGNORECASE,
)


def _slug_matches_target_funding(url: str) -> bool:
    """Return True if a sitemap article URL slug points to a target-sector funding round."""
    if _SITEMAP_SKIP_SLUG_RE.search(url):
        return False
    return bool(_SITEMAP_TARGET_SLUG_RE.search(url) and _SITEMAP_FUNDING_SLUG_RE.search(url))


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

        # Drop articles that do not contain funding signal keywords in their title.
        # This avoids sending irrelevant general-news articles through the
        # expensive extraction phase.
        if not _title_has_funding_signal(title):
            self._logger.debug("Title-filter skip (no funding signal): %s", title)
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


class WPRestSource(RSSSource):
    """
    Shared RSS + WordPress REST API (``/wp-json/wp/v2/posts``) adapter.

    Subclasses set ``WP_API_URL`` and ``WP_SEARCH_TERMS`` to pull verified
    historical articles strictly within ``[start_date, end_date]`` alongside
    standard RSS feeds.
    """

    WP_API_URL: str = ""
    WP_SEARCH_TERMS: list[str] = []
    WP_PER_PAGE: int = 25
    WP_MAX_PAGES: int = 2

    def discover(self) -> Iterator[Article]:
        yield from super().discover()
        if self.WP_API_URL:
            yield from self._discover_wp_api()

    def _discover_wp_api(self) -> Iterator[Article]:
        terms = self.WP_SEARCH_TERMS or [""]
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
        }
        after_iso = f"{self.start_date.isoformat()}T00:00:00"
        before_iso = f"{self.end_date.isoformat()}T23:59:59"

        for term in terms:
            for page in range(1, self.WP_MAX_PAGES + 1):
                params = {
                    "after": after_iso,
                    "before": before_iso,
                    "per_page": self.WP_PER_PAGE,
                    "page": page,
                }
                if term:
                    params["search"] = term

                resp = self._get(self.WP_API_URL, params=params, headers=headers)
                if resp is None or resp.status_code != 200:
                    break
                try:
                    posts = resp.json()
                except Exception:
                    break
                if not isinstance(posts, list) or not posts:
                    break

                for post in posts:
                    url = post.get("link")
                    raw_title = (post.get("title") or {}).get("rendered", "")
                    title = html_lib.unescape(raw_title).strip()
                    if not url or not title:
                        continue
                    if not _title_has_funding_signal(title):
                        continue

                    canonical = canonicalize_url(url)
                    if canonical in self._seen_urls:
                        continue

                    raw_date = post.get("date_gmt") or post.get("date")
                    published_at = None
                    if raw_date:
                        try:
                            dt = dateutil_parser.parse(raw_date)
                            published_at = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
                        except Exception:
                            pass

                    rendered_body = (post.get("content") or {}).get("rendered", "")
                    body_text = _extract_wp_body_text(rendered_body)
                    rendered_excerpt = (post.get("excerpt") or {}).get("rendered", "")
                    summary = _extract_wp_body_text(rendered_excerpt)[:500] if rendered_excerpt else None

                    self._seen_urls.add(canonical)
                    yield Article(
                        url=url,
                        canonical_url=canonical,
                        title=title,
                        source_id=self.SOURCE_ID,
                        source_name=self.SOURCE_NAME,
                        summary=summary,
                        full_text=body_text if len(body_text) >= 120 else None,
                        published_at=published_at,
                        feed_url=self.WP_API_URL,
                        discovery_query=term or None,
                        extraction_status=ExtractionStatus.SUCCESS if len(body_text) >= 120 else ExtractionStatus.PENDING,
                    )

                if len(posts) < self.WP_PER_PAGE:
                    break
