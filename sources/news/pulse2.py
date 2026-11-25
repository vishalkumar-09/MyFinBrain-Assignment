"""
sources/news/pulse2.py
=====================
Pulse 2.0 adapter covering US venture funding rounds in wealth management,
private funds technology, alternative assets, and financial infrastructure.
"""
from __future__ import annotations

from sources.rss_source import WPRestSource
from sources import registry


@registry.register
class Pulse2Source(WPRestSource):
    SOURCE_ID = "pulse2"
    SOURCE_NAME = "Pulse 2.0"
    RSS_FEEDS = []
    WP_API_URL = "https://pulse2.com/wp-json/wp/v2/posts"
    WP_SEARCH_TERMS = [
        "wealth management",
        "wealthtech",
        "private funds",
        "private markets",
        "alternative investment",
        "investment risk",
        "tokenized",
        "portfolio management",
        "advisory platform",
        "risk markets",
        "prediction market",
        "land markets",
    ]
    WP_PER_PAGE = 20
    WP_MAX_PAGES = 2
