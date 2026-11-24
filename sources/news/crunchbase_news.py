"""
sources/news/crunchbase_news.py
===============================
Crunchbase News RSS adapter.
"""
from __future__ import annotations

from sources.rss_source import RSSSource
from sources import registry


@registry.register
class CrunchbaseNewsSource(RSSSource):
    SOURCE_ID = "crunchbase_news"
    SOURCE_NAME = "Crunchbase News"
    RSS_FEEDS = [
        "https://news.crunchbase.com/feed/",
    ]
