"""
sources/news/fintech_global.py
=============================
FinTech Global adapter covering US and global WealthTech, Asset Management,
Private Markets, and Investment Infrastructure announcements.
"""
from __future__ import annotations

from sources.rss_source import WPRestSource
from sources import registry


@registry.register
class FinTechGlobalSource(WPRestSource):
    SOURCE_ID = "fintech_global"
    SOURCE_NAME = "FinTech Global"
    RSS_FEEDS = [
        "https://fintech.global/feed/",
    ]
    WP_API_URL = "https://fintech.global/wp-json/wp/v2/posts"
    WP_SEARCH_TERMS = [
        "wealthtech",
        "wealth management",
        "private equity",
        "private credit",
        "private markets",
        "alternative investment",
        "alternatives infrastructure",
        "portfolio management",
        "registered investment",
        "family office",
        "investment research",
        "hedge fund",
        "tokenised",
    ]
    WP_PER_PAGE = 25
    WP_MAX_PAGES = 2
