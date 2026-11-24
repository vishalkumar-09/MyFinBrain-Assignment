"""
sources/news/sifted.py
======================
Sifted adapter – European startup news with US/India deal coverage.
"""
from __future__ import annotations

from sources.rss_source import RSSSource
from sources import registry


@registry.register
class SiftedSource(RSSSource):
    SOURCE_ID = "sifted"
    SOURCE_NAME = "Sifted"
    RSS_FEEDS = [
        "https://sifted.eu/feed/",
        "https://sifted.eu/sector/fintech/feed/",
    ]
