"""
sources/bing_news.py
====================
Bing News RSS discovery adapter with direct publisher URL extraction.

Bing News RSS search links encode the true destination publisher URL inside
the ``url=`` query parameter, avoiding opaque redirect tokens and allowing
direct fetching of original articles across the entire target date range.
"""
from __future__ import annotations

import logging
import urllib.parse
from datetime import date
from typing import Iterator, Optional

import feedparser

from config.settings import (
    END_DATE,
    REQUEST_DELAY_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    START_DATE,
    USER_AGENT,
)
from sources import registry
from sources.base import Article, ExtractionStatus, canonicalize_url
from sources.rss_source import RSSSource, _parse_feed_date, _title_has_funding_signal

logger = logging.getLogger(__name__)

_BING_NEWS_BASE = "https://www.bing.com/news/search"

# Hard-paywalled, reliably blocked, or noisy/inaccurate rewrite domains
_SKIP_DOMAINS = frozenset({
    "wsj.com",
    "ft.com",
    "barrons.com",
    "bloomberg.com",
    "citywire.com",
    "msn.com",
    "indianstartuptimes.com",
})

_DEFAULT_BING_QUERIES = [
    '"wealth management" startup raises funding 2026',
    '"wealthtech" startup raises Series 2026',
    '"private equity" platform raises million 2026',
    '"private credit" startup raises million 2026',
    '"private markets" platform raises million 2026',
    '"alternative investment" platform raises million 2026',
    '"registered investment advisor" raises million 2026',
    '"family office" software raises million 2026',
    '"portfolio management" startup raises million 2026',
    '"capital markets" startup raises million Series 2026',
    'wealthtech India raises crore million 2026',
    '"wealth-tech" India raises crore 2026',
    'Peak XV wealthtech Rs crore 2026',
    '"wealth management" India raises crore million 2026',
    '"alternative investment" India raises crore 2026',
    'fintech wealthtech India raises crore 2026',
    'tokenised fund investment raises million 2026',
]


def extract_direct_publisher_url(bing_link: str) -> str:
    """Decode Bing News apiclick wrapper URL into its underlying publisher URL."""
    if not bing_link:
        return bing_link
    try:
        parsed = urllib.parse.urlparse(bing_link)
        if "bing.com" in parsed.netloc and "url=" in parsed.query:
            qs = urllib.parse.parse_qs(parsed.query)
            if "url" in qs and qs["url"]:
                return qs["url"][0]
    except Exception:
        pass
    return bing_link


_KNOWN_PUBLISHERS = {
    "techcrunch.com": "TechCrunch",
    "inc42.com": "Inc42",
    "yourstory.com": "YourStory",
    "entrackr.com": "Entrackr",
    "economictimes.indiatimes.com": "Economic Times",
    "fintech.global": "FinTech Global",
    "pulse2.com": "Pulse 2.0",
    "alleywatch.com": "AlleyWatch",
    "prnewswire.com": "PR Newswire",
    "businesswire.com": "Business Wire",
    "finance.yahoo.com": "Yahoo Finance",
    "uk.finance.yahoo.com": "Yahoo Finance",
    "morningstar.com": "Morningstar",
    "markets.businessinsider.com": "Business Insider",
    "thehindubusinessline.com": "The Hindu BusinessLine",
    "indianstartupnews.com": "Indian Startup News",
    "indianstartuptimes.com": "Indian Startup Times",
    "entrepreneur.com": "Entrepreneur India",
    "india.entrepreneur.com": "Entrepreneur India",
    "cryptobriefing.com": "CryptoBriefing",
    "techfundingnews.com": "Tech Funding News",
    "citybiz.co": "CityBiz",
    "ibsintelligence.com": "IBS Intelligence",
    "livemint.com": "Mint",
    "moneycontrol.com": "Moneycontrol",
    "business-standard.com": "Business Standard",
    "vccircle.com": "VCCircle",
    "fortuneindia.com": "Fortune India",
    "financialexpress.com": "Financial Express",
    "deccanherald.com": "Deccan Herald",
    "unite.ai": "Unite.AI",
    "hubbis.com": "Hubbis",
    "theaiinsider.tech": "The AI Insider",
}


def _publisher_name_from_url(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if host in _KNOWN_PUBLISHERS:
        return _KNOWN_PUBLISHERS[host]
    for domain, name in _KNOWN_PUBLISHERS.items():
        if host.endswith(f".{domain}"):
            return name
    parts = host.split(".")
    return parts[0].title() if parts and parts[0] else "Bing News"


@registry.register
class BingNewsSource(RSSSource):
    """
    Search-based news discovery via Bing News RSS, extracting direct publisher URLs.
    """

    SOURCE_ID = "bing_news"
    SOURCE_NAME = "Bing News"

    def __init__(
        self,
        start_date: date = START_DATE,
        end_date: date = END_DATE,
        user_agent: str = USER_AGENT,
        request_delay: float = max(REQUEST_DELAY_SECONDS, 1.0),
        timeout: int = REQUEST_TIMEOUT_SECONDS,
        custom_queries: Optional[list[str]] = None,
    ) -> None:
        super().__init__(
            start_date=start_date,
            end_date=end_date,
            rss_feeds=[],
            user_agent=user_agent,
            request_delay=request_delay,
            timeout=timeout,
        )
        self._queries = custom_queries if custom_queries is not None else list(_DEFAULT_BING_QUERIES)

    def discover(self) -> Iterator[Article]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
        }
        for query in self._queries:
            params = urllib.parse.urlencode({"q": query, "format": "rss"})
            feed_url = f"{_BING_NEWS_BASE}?{params}"
            resp = self._get(feed_url, headers=headers)
            if resp is None or resp.status_code != 200:
                continue

            feed = feedparser.parse(resp.text)
            for entry in feed.entries:
                raw_link = getattr(entry, "link", None)
                title = (getattr(entry, "title", "") or "").strip()
                if not raw_link or not title:
                    continue
                if not _title_has_funding_signal(title):
                    continue

                direct_url = extract_direct_publisher_url(raw_link)
                domain = urllib.parse.urlparse(direct_url).netloc.lower()
                if any(domain == d or domain.endswith(f".{d}") for d in _SKIP_DOMAINS):
                    continue

                canonical = canonicalize_url(direct_url)
                if canonical in self._seen_urls:
                    continue

                pub_at = _parse_feed_date(entry)
                if pub_at is not None and not (self.start_date <= pub_at.date() <= self.end_date):
                    continue

                summary = getattr(entry, "description", None) or getattr(entry, "summary", None)
                self._seen_urls.add(canonical)
                yield Article(
                    url=direct_url,
                    canonical_url=canonical,
                    title=title,
                    source_id=self.SOURCE_ID,
                    source_name=_publisher_name_from_url(direct_url),
                    summary=summary.strip() if summary else None,
                    published_at=pub_at,
                    feed_url=feed_url,
                    discovery_query=query,
                    extraction_status=ExtractionStatus.PENDING,
                )
