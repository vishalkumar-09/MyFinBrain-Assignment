"""
sources/news/prnewswire.py
==========================
PR Newswire adapter.

PR Newswire provides a general news-releases feed.
Category-specific feeds also available via subject codes:
  fin  = Financial Services (we target this)
  tec  = Technology
"""
from __future__ import annotations

from sources.rss_source import RSSSource
from sources import registry


@registry.register
class PRNewswireSource(RSSSource):
    SOURCE_ID = "prnewswire"
    SOURCE_NAME = "PR Newswire"
    RSS_FEEDS = [
        "https://www.prnewswire.com/rss/news-releases-list.rss",
        "https://www.prnewswire.com/rss/financial-services-latest-news.rss",
        "https://www.prnewswire.com/rss/technology-latest-news.rss",
    ]
