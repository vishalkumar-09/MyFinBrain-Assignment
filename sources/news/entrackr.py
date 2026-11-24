"""
sources/news/entrackr.py
========================
Entrackr adapter – focused on Indian startup funding data.
"""
from __future__ import annotations

from sources.rss_source import RSSSource
from sources import registry


@registry.register
class EntrackrSource(RSSSource):
    SOURCE_ID = "entrackr"
    SOURCE_NAME = "Entrackr"
    RSS_FEEDS = [
        "https://entrackr.com/feed/",
        "https://entrackr.com/category/funding/feed/",
    ]
