"""
sources/news/inc42.py
=====================
Inc42 adapter – leading Indian startup news.

Combines Inc42 RSS feeds with WordPress REST API historical search so runs
capture the full configured date window across Indian wealth management,
alternative investments, private markets, and adjacent fintech.
"""
from __future__ import annotations

from sources.rss_source import WPRestSource
from sources import registry


@registry.register
class Inc42Source(WPRestSource):
    SOURCE_ID = "inc42"
    SOURCE_NAME = "Inc42"
    RSS_FEEDS = [
        "https://inc42.com/feed/",
        "https://inc42.com/tag/funding/feed/",
        "https://inc42.com/tag/fintech/feed/",
        "https://inc42.com/tag/investment/feed/",
    ]
    WP_API_URL = "https://inc42.com/wp-json/wp/v2/posts"
    WP_SEARCH_TERMS = [
        "wealthtech",
        "wealth management",
        "alternative investment",
        "private credit",
        "private equity",
        "fixed income",
        "corporate bonds",
        "trading platform",
        "investment platform",
        "brokerage",
        "pre-ipo",
    ]
    WP_PER_PAGE = 25
    WP_MAX_PAGES = 2
