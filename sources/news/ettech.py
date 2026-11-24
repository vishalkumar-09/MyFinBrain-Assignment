"""
sources/news/ettech.py
======================
Economic Times Tech adapter.
ET provides category RSS feeds organised by section id.
"""
from __future__ import annotations

from sources.rss_source import RSSSource
from sources import registry


@registry.register
class ETTechSource(RSSSource):
    SOURCE_ID = "ettech"
    SOURCE_NAME = "ET Tech"
    RSS_FEEDS = [
        # Tech/Startups section
        "https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms",
        # Funding & VC
        "https://economictimes.indiatimes.com/small-biz/startups/funding/rssfeeds/7102581.cms",
    ]
