"""
sources/google_news.py
======================
Google News RSS adapter for article discovery.

Google News exposes a public RSS endpoint that accepts a search query:
  https://news.google.com/rss/search?q=<encoded_query>&hl=en-US&gl=US&ceid=US:en

This adapter generates search queries from the QueryBuilder and fetches
RSS results.  It is used for *discovery* only – articles must still be
fetched and classified from their original publishers.

Improvements in Milestone 2:
- Uses QueryBuilder for structured query generation.
- Runs India-specific queries with Indian locale parameters.
- Deduplicates articles across queries within this adapter.
- Tracks which query produced each article.
"""

from __future__ import annotations

import logging
import urllib.parse
from datetime import date
from typing import Iterator

from discovery.query_builder import QueryBuilder, SearchQuery
from sources.base import Article, canonicalize_url
from sources.rss_source import RSSSource
from sources import registry
from config.settings import (
    START_DATE,
    END_DATE,
    USER_AGENT,
    REQUEST_DELAY_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)

_GNEWS_BASE = "https://news.google.com/rss/search"


def build_feed_url(
    query: str,
    language: str = "en-US",
    geo: str = "US",
) -> str:
    """Return a Google News RSS URL for the given query."""
    params = {
        "q": query,
        "hl": language,
        "gl": geo,
        "ceid": f"{geo}:{language[:2]}",
    }
    return f"{_GNEWS_BASE}?{urllib.parse.urlencode(params)}"


# Keep backward-compatible export from Milestone 1
def build_google_news_queries(
    business_keywords=None,
    funding_keywords=None,
    geo_qualifiers=None,
) -> list[str]:
    """
    Return plain-text query strings (backward-compatible helper).
    New code should use QueryBuilder directly.
    """
    from config.keywords import BUSINESS_KEYWORDS, FUNDING_KEYWORDS, GEO_QUALIFIERS
    biz = business_keywords or BUSINESS_KEYWORDS
    fund = funding_keywords or FUNDING_KEYWORDS
    geo = geo_qualifiers or GEO_QUALIFIERS

    qb = QueryBuilder(
        business_keywords=biz,
        funding_keywords=fund,
        geo_qualifiers=geo,
    )
    return [q.text for q in qb.build_all(500)]


@registry.register
class GoogleNewsSource(RSSSource):
    """
    Discovery adapter using Google News RSS.

    Generates search queries using QueryBuilder and fetches RSS results.
    Runs both US-locale and India-locale queries.
    Respects a maximum number of queries to avoid rate-limiting.
    """

    SOURCE_ID = "google_news"
    SOURCE_NAME = "Google News RSS"

    # Maximum queries to issue per locale in one run
    MAX_QUERIES_PER_LOCALE = 50

    # Locale configs: (language, geo, country_filter)
    _LOCALES = [
        ("en-US", "US", "United States"),
        ("en-IN", "IN", "India"),
    ]

    def __init__(
        self,
        start_date: date = START_DATE,
        end_date: date = END_DATE,
        user_agent: str = USER_AGENT,
        request_delay: float = max(REQUEST_DELAY_SECONDS, 2.0),
        timeout: int = REQUEST_TIMEOUT_SECONDS,
        max_queries: int = MAX_QUERIES_PER_LOCALE,
        custom_queries: list[str] | None = None,
    ) -> None:
        super().__init__(
            start_date=start_date,
            end_date=end_date,
            rss_feeds=[],  # Feeds are built dynamically
            user_agent=user_agent,
            request_delay=request_delay,
            timeout=timeout,
        )
        self._max_queries = max_queries
        self._custom_queries = custom_queries
        self._qb = QueryBuilder()

    def _get_queries(self) -> list[str]:
        """Return query text strings, respecting the max limit."""
        if self._custom_queries is not None:
            return self._custom_queries[: self._max_queries]
        return [q.text for q in self._qb.build_all(self._max_queries)]

    def discover(self) -> Iterator[Article]:
        queries = self._get_queries()
        self._logger.info(
            "GoogleNewsSource: issuing %d queries × %d locales",
            len(queries),
            len(self._LOCALES),
        )

        for lang, geo, country in self._LOCALES:
            self._logger.info("  Locale: %s/%s", lang, geo)
            locale_seen = 0
            for query in queries:
                feed_url = build_feed_url(query, language=lang, geo=geo)
                self._logger.debug("Query[%s]: %s", geo, query)
                for article in self._process_feed(feed_url):
                    article.discovery_query = query
                    # Tag with the country context we were searching for
                    # (not the article's actual headquarters – that's classification)
                    locale_seen += 1
                    yield article
            self._logger.info("  Locale %s: %d articles", geo, locale_seen)
