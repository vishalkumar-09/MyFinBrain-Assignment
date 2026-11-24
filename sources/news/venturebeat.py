"""
sources/news/venturebeat.py
============================
VentureBeat adapter.
"""
from __future__ import annotations

from sources.rss_source import RSSSource
from sources import registry


@registry.register
class VentureBeatSource(RSSSource):
    SOURCE_ID = "venturebeat"
    SOURCE_NAME = "VentureBeat"
    RSS_FEEDS = [
        "https://venturebeat.com/feed/",
        "https://venturebeat.com/category/business/feed/",
        "https://venturebeat.com/category/ai/feed/",
    ]
