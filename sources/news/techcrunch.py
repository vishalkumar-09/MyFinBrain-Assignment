"""
sources/news/techcrunch.py
===========================
TechCrunch adapter combining RSS feeds with WordPress REST API discovery
over the configured date range.
"""
from __future__ import annotations

from sources.rss_source import WPRestSource
from sources import registry


@registry.register
class TechCrunchSource(WPRestSource):
    SOURCE_ID = "techcrunch"
    SOURCE_NAME = "TechCrunch"
    RSS_FEEDS = [
        "https://techcrunch.com/feed/",
        "https://techcrunch.com/tag/funding/feed/",
        "https://techcrunch.com/tag/venture-capital/feed/",
        "https://techcrunch.com/tag/startups/feed/",
        "https://techcrunch.com/category/fintech/feed/",
    ]
    WP_API_URL = "https://techcrunch.com/wp-json/wp/v2/posts"
    WP_SEARCH_TERMS = [
        "wealth management",
        "wealthtech",
        "private equity",
        "private credit",
        "alternative investment",
        "registered investment",
        "family office",
        "stock portfolios",
        "investment banking",
    ]
    WP_PER_PAGE = 25
    WP_MAX_PAGES = 1
