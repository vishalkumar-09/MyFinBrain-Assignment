"""
sources/news/techcrunch.py
===========================
TechCrunch adapter with enriched feed list.

TechCrunch provides multiple RSS feeds:
 - Main feed         : /feed/
 - Funding tag       : /tag/funding/feed/
 - Venture capital   : /tag/venture-capital/feed/
 - Startup tag       : /tag/startups/feed/
 - Category: Fintech : /category/fintech/feed/

No authentication required. No API key needed.
Respect their robots.txt (crawl-delay: 10).
"""
from __future__ import annotations

from sources.rss_source import RSSSource
from sources import registry


@registry.register
class TechCrunchSource(RSSSource):
    SOURCE_ID = "techcrunch"
    SOURCE_NAME = "TechCrunch"
    RSS_FEEDS = [
        "https://techcrunch.com/feed/",
        "https://techcrunch.com/tag/funding/feed/",
        "https://techcrunch.com/tag/venture-capital/feed/",
        "https://techcrunch.com/tag/startups/feed/",
        "https://techcrunch.com/category/fintech/feed/",
    ]
