"""
sources/news/yourstory.py
=========================
YourStory adapter – Indian startup and entrepreneur news.
"""
from __future__ import annotations

from sources.rss_source import RSSSource
from sources import registry


@registry.register
class YourStorySource(RSSSource):
    SOURCE_ID = "yourstory"
    SOURCE_NAME = "YourStory"
    RSS_FEEDS = [
        "https://yourstory.com/feed",
        "https://yourstory.com/tag/funding/feed",
        "https://yourstory.com/tag/investment/feed",
    ]
