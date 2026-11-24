"""
sources/news/inc42.py
=====================
Inc42 adapter – leading Indian startup news.

Feed catalogue:
 - Main feed         : /feed/
 - Funding tag       : /tag/funding/feed/
 - Fintech tag       : /tag/fintech/feed/
 - Investment tag    : /tag/investment/feed/
"""
from __future__ import annotations

from sources.rss_source import RSSSource
from sources import registry


@registry.register
class Inc42Source(RSSSource):
    SOURCE_ID = "inc42"
    SOURCE_NAME = "Inc42"
    RSS_FEEDS = [
        "https://inc42.com/feed/",
        "https://inc42.com/tag/funding/feed/",
        "https://inc42.com/tag/fintech/feed/",
        "https://inc42.com/tag/investment/feed/",
    ]
