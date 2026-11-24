"""
sources/news/businesswire.py
============================
Business Wire adapter.

Business Wire provides public RSS feeds broken out by industry.
Relevant industry codes:
  G22 = Technology
  G56 = Financial Services
  G34 = Investment & Securities
"""
from __future__ import annotations

from sources.rss_source import RSSSource
from sources import registry


@registry.register
class BusinessWireSource(RSSSource):
    SOURCE_ID = "businesswire"
    SOURCE_NAME = "Business Wire"
    RSS_FEEDS = [
        # Technology
        "https://feed.businesswire.com/rss/home/?rss=G22&rssid=0",
        # Financial Services
        "https://feed.businesswire.com/rss/home/?rss=G56&rssid=0",
        # Investment & Securities
        "https://feed.businesswire.com/rss/home/?rss=G34&rssid=0",
    ]
