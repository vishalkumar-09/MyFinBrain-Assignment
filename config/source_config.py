"""
config/source_config.py
=======================
Per-source configuration: RSS feed URLs, rate limits, enabled/disabled flag,
and access notes.  This is the single place to update when a source changes
its URL or requires a new API key.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class SourceConfig:
    """Immutable configuration record for one data source."""

    source_id: str
    display_name: str
    base_url: str
    rss_feeds: list[str] = field(default_factory=list)
    enabled: bool = True
    requires_api_key: bool = False
    api_key_env_var: Optional[str] = None
    # Seconds to wait between requests to this source
    request_delay: float = 1.0
    # Maximum requests per minute (0 = unlimited / best-effort)
    rate_limit_rpm: int = 20
    access_notes: str = ""


# ---------------------------------------------------------------------------
# Source registry
# ---------------------------------------------------------------------------
SOURCE_CONFIGS: dict[str, SourceConfig] = {
    # ------------------------------------------------------------------
    # News / Editorial
    # ------------------------------------------------------------------
    "techcrunch": SourceConfig(
        source_id="techcrunch",
        display_name="TechCrunch",
        base_url="https://techcrunch.com",
        rss_feeds=[
            "https://techcrunch.com/feed/",
            "https://techcrunch.com/tag/funding/feed/",
            "https://techcrunch.com/tag/venture-capital/feed/",
        ],
        request_delay=1.5,
    ),
    "crunchbase_news": SourceConfig(
        source_id="crunchbase_news",
        display_name="Crunchbase News",
        base_url="https://news.crunchbase.com",
        rss_feeds=["https://news.crunchbase.com/feed/"],
        request_delay=1.5,
    ),
    "businesswire": SourceConfig(
        source_id="businesswire",
        display_name="Business Wire",
        base_url="https://www.businesswire.com",
        rss_feeds=[
            "https://feed.businesswire.com/rss/home/?rss=G1&rssid=0",
            "https://feed.businesswire.com/rss/home/?rss=G22&rssid=0",  # Technology
        ],
        request_delay=1.0,
    ),
    "prnewswire": SourceConfig(
        source_id="prnewswire",
        display_name="PR Newswire",
        base_url="https://www.prnewswire.com",
        rss_feeds=[
            "https://www.prnewswire.com/rss/news-releases-list.rss",
        ],
        request_delay=1.0,
        access_notes="Public RSS feed; full article available on site.",
    ),
    "venturebeat": SourceConfig(
        source_id="venturebeat",
        display_name="VentureBeat",
        base_url="https://venturebeat.com",
        rss_feeds=[
            "https://venturebeat.com/feed/",
            "https://venturebeat.com/category/business/feed/",
        ],
        request_delay=1.5,
    ),
    "sifted": SourceConfig(
        source_id="sifted",
        display_name="Sifted",
        base_url="https://sifted.eu",
        rss_feeds=["https://sifted.eu/feed/"],
        request_delay=1.5,
        access_notes="European focus; covers some US/India cross-border deals.",
    ),
    # ------------------------------------------------------------------
    # Indian startup news
    # ------------------------------------------------------------------
    "inc42": SourceConfig(
        source_id="inc42",
        display_name="Inc42",
        base_url="https://inc42.com",
        rss_feeds=[
            "https://inc42.com/feed/",
            "https://inc42.com/tag/funding/feed/",
        ],
        request_delay=1.5,
    ),
    "entrackr": SourceConfig(
        source_id="entrackr",
        display_name="Entrackr",
        base_url="https://entrackr.com",
        rss_feeds=["https://entrackr.com/feed/"],
        request_delay=1.5,
    ),
    "yourstory": SourceConfig(
        source_id="yourstory",
        display_name="YourStory",
        base_url="https://yourstory.com",
        rss_feeds=["https://yourstory.com/feed"],
        request_delay=1.5,
    ),
    "ettech": SourceConfig(
        source_id="ettech",
        display_name="ET Tech",
        base_url="https://economictimes.indiatimes.com/tech",
        rss_feeds=[
            "https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms",
        ],
        request_delay=2.0,
    ),
    "vccircle": SourceConfig(
        source_id="vccircle",
        display_name="VCCircle",
        base_url="https://www.vccircle.com",
        rss_feeds=["https://www.vccircle.com/feed/"],
        request_delay=1.5,
        access_notes="Some content may be behind a paywall.",
    ),
    # ------------------------------------------------------------------
    # Structured databases (require API keys or export files)
    # ------------------------------------------------------------------
    "crunchbase": SourceConfig(
        source_id="crunchbase",
        display_name="Crunchbase",
        base_url="https://www.crunchbase.com",
        rss_feeds=[],
        requires_api_key=True,
        api_key_env_var="CRUNCHBASE_API_KEY",
        access_notes="Requires paid API key (Basic or Pro). Adapter reads from API if key is configured.",
    ),
    "tracxn": SourceConfig(
        source_id="tracxn",
        display_name="Tracxn",
        base_url="https://tracxn.com",
        rss_feeds=[],
        requires_api_key=True,
        api_key_env_var="TRACXN_API_KEY",
        access_notes="Requires Tracxn API key.",
    ),
    "dealroom": SourceConfig(
        source_id="dealroom",
        display_name="Dealroom",
        base_url="https://dealroom.co",
        rss_feeds=[],
        requires_api_key=True,
        api_key_env_var="DEALROOM_API_KEY",
        access_notes="Requires Dealroom API key.",
    ),
    "pitchbook": SourceConfig(
        source_id="pitchbook",
        display_name="PitchBook",
        base_url="https://pitchbook.com",
        rss_feeds=[],
        requires_api_key=False,
        access_notes="No public API. Adapter reads from user-exported CSV/Excel files. Configure PITCHBOOK_EXPORT_PATH.",
    ),
    "cb_insights": SourceConfig(
        source_id="cb_insights",
        display_name="CB Insights",
        base_url="https://www.cbinsights.com",
        rss_feeds=[],
        requires_api_key=True,
        api_key_env_var="CB_INSIGHTS_API_KEY",
        access_notes="Requires CB Insights API access.",
    ),
    # ------------------------------------------------------------------
    # Discovery / verification
    # ------------------------------------------------------------------
    "google_news": SourceConfig(
        source_id="google_news",
        display_name="Google News RSS",
        base_url="https://news.google.com",
        rss_feeds=[],  # URLs are built dynamically from queries
        request_delay=2.0,
        rate_limit_rpm=10,
        access_notes="Discovery only. RSS feeds require query-specific URL construction.",
    ),
    "sec_edgar": SourceConfig(
        source_id="sec_edgar",
        display_name="SEC EDGAR",
        base_url="https://efts.sec.gov/LATEST/search-index",
        rss_feeds=[],
        request_delay=0.5,
        rate_limit_rpm=10,
        access_notes="Public EDGAR full-text search API. Rate limit: 10 req/s. Used for Form D filings.",
    ),
    "startup_india": SourceConfig(
        source_id="startup_india",
        display_name="Startup India",
        base_url="https://www.startupindia.gov.in",
        rss_feeds=[],
        request_delay=2.0,
        access_notes="Public directory. Scraping subject to ToS review.",
    ),
    "ycombinator": SourceConfig(
        source_id="ycombinator",
        display_name="Y Combinator Portfolio",
        base_url="https://www.ycombinator.com/companies",
        rss_feeds=[],
        request_delay=2.0,
        access_notes="Public company directory; no structured API. Used for verification only.",
    ),
    "antler": SourceConfig(
        source_id="antler",
        display_name="Antler Portfolio",
        base_url="https://www.antler.co/portfolio",
        rss_feeds=[],
        request_delay=2.0,
        access_notes="Public portfolio page. Used for verification only.",
    ),
}


def get_source_config(source_id: str) -> Optional[SourceConfig]:
    """Return the config for a source, or None if not found."""
    return SOURCE_CONFIGS.get(source_id)


def get_enabled_sources() -> list[SourceConfig]:
    """Return all enabled source configs."""
    return [cfg for cfg in SOURCE_CONFIGS.values() if cfg.enabled]


def get_rss_sources() -> list[SourceConfig]:
    """Return enabled sources that have at least one RSS feed."""
    return [cfg for cfg in get_enabled_sources() if cfg.rss_feeds]
