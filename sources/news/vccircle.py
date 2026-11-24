"""
sources/news/vccircle.py
========================
VCCircle adapter – Indian VC and PE news.

Note: Some full articles are behind a registration wall.
The RSS feed provides titles and summaries which are sufficient for
discovery-phase filtering.
"""
from __future__ import annotations

from sources.rss_source import RSSSource
from sources import registry


@registry.register
class VCCircleSource(RSSSource):
    SOURCE_ID = "vccircle"
    SOURCE_NAME = "VCCircle"
    RSS_FEEDS = [
        "https://www.vccircle.com/feed/",
        "https://www.vccircle.com/category/technology/feed/",
        "https://www.vccircle.com/category/financial-services/feed/",
    ]
