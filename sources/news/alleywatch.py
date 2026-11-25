"""
sources/news/alleywatch.py
=========================
AlleyWatch adapter covering New York City startup funding rounds,
including capital markets, wealthtech, and alternative investment infrastructure.
"""
from __future__ import annotations

from sources.rss_source import WPRestSource
from sources import registry


@registry.register
class AlleyWatchSource(WPRestSource):
    SOURCE_ID = "alleywatch"
    SOURCE_NAME = "AlleyWatch"
    RSS_FEEDS = [
        "https://www.alleywatch.com/feed/",
    ]
    WP_API_URL = "https://www.alleywatch.com/wp-json/wp/v2/posts"
    WP_SEARCH_TERMS = [
        "wealth management",
        "hedge fund",
        "capital markets",
        "investment research",
        "private credit",
        "private equity",
        "portfolio",
        "fintech",
    ]
    WP_PER_PAGE = 20
    WP_MAX_PAGES = 1
