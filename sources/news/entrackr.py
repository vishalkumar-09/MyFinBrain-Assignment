"""
sources/news/entrackr.py
========================
Entrackr adapter – focused on Indian startup funding data.

Combines Entrackr's live RSS feed (``/rss``) with date-bounded daily XML
sitemap scanning (``sitemap_YYYY-MM-DD.xml``) so historical deals across
the full configured window are discovered automatically.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Iterator

from sources.base import Article, ExtractionStatus, canonicalize_url
from sources.rss_source import RSSSource, _slug_matches_target_funding
from sources import registry


@registry.register
class EntrackrSource(RSSSource):
    SOURCE_ID = "entrackr"
    SOURCE_NAME = "Entrackr"
    RSS_FEEDS = [
        "https://entrackr.com/rss",
    ]
    SITEMAP_INDEX_URL = "https://entrackr.com/sitemap.xml"

    def discover(self) -> Iterator[Article]:
        yield from super().discover()
        yield from self._discover_from_sitemaps()

    def _discover_from_sitemaps(self) -> Iterator[Article]:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
        }
        resp = self._get(self.SITEMAP_INDEX_URL, headers=headers)
        if resp is None or resp.status_code != 200:
            return

        daily_maps = re.findall(r"<loc>(https://entrackr\.com/sitemap_(\d{4}-\d{2}-\d{2})\.xml)</loc>", resp.text)
        for sm_url, date_str in daily_maps:
            try:
                sm_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                continue
            if sm_date < self.start_date or sm_date > self.end_date:
                continue

            sm_resp = self._get(sm_url, headers=headers)
            if sm_resp is None or sm_resp.status_code != 200:
                continue

            pub_dt = datetime(sm_date.year, sm_date.month, sm_date.day, 12, 0, tzinfo=timezone.utc)
            for article_url in re.findall(r"<loc>(.*?)</loc>", sm_resp.text):
                if not _slug_matches_target_funding(article_url):
                    continue
                canonical = canonicalize_url(article_url)
                if canonical in self._seen_urls:
                    continue
                self._seen_urls.add(canonical)
                # Build readable temporary title from URL slug; overwritten on HTML parse
                slug = article_url.rstrip("/").split("/")[-1]
                slug = re.sub(r"-\d{6,}$", "", slug)
                temp_title = slug.replace("-", " ").strip().title()
                yield Article(
                    url=article_url,
                    canonical_url=canonical,
                    title=temp_title or "Entrackr Funding Report",
                    source_id=self.SOURCE_ID,
                    source_name=self.SOURCE_NAME,
                    published_at=pub_dt,
                    feed_url=sm_url,
                    discovery_query="sitemap_slug",
                    extraction_status=ExtractionStatus.PENDING,
                )
