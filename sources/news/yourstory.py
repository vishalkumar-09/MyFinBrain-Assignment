"""
sources/news/yourstory.py
=========================
YourStory adapter – Indian startup and entrepreneur news.

Combines YourStory RSS feeds with weekly XML sitemap discovery filtered to
[start_date, end_date] and target wealth/investment funding slugs.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Iterator

from sources.base import Article, ExtractionStatus, canonicalize_url
from sources.rss_source import RSSSource, _slug_matches_target_funding
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
    SITEMAP_INDEX_URL = "https://yourstory.com/sitemap.xml"

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

        weekly_maps = re.findall(r"<loc>(https://yourstory\.com/sitemap_(\d{4})_week(\d+)\.xml)</loc>", resp.text)
        start_year, start_week, _ = self.start_date.isocalendar()
        end_year, end_week, _ = self.end_date.isocalendar()

        for sm_url, year_s, week_s in weekly_maps:
            yr, wk = int(year_s), int(week_s)
            if (yr, wk) < (start_year, start_week - 1) or (yr, wk) > (end_year, end_week + 1):
                continue

            sm_resp = self._get(sm_url, headers=headers)
            if sm_resp is None or sm_resp.status_code != 200:
                continue

            for article_url in re.findall(r"<loc>(.*?)</loc>", sm_resp.text):
                if not _slug_matches_target_funding(article_url):
                    continue
                canonical = canonicalize_url(article_url)
                if canonical in self._seen_urls:
                    continue

                # YourStory URLs encode /YYYY/MM/
                pub_dt = None
                m_ym = re.search(r"/(\d{4})/(\d{2})/", article_url)
                if m_ym:
                    ym_y, ym_m = int(m_ym.group(1)), int(m_ym.group(2))
                    if date(ym_y, ym_m, 1) > self.end_date:
                        continue
                    # Reject months clearly completely before start_date
                    if ym_y < self.start_date.year or (ym_y == self.start_date.year and ym_m < self.start_date.month):
                        continue
                    pub_dt = datetime(ym_y, ym_m, 15, 12, 0, tzinfo=timezone.utc)

                self._seen_urls.add(canonical)
                slug = article_url.rstrip("/").split("/")[-1]
                temp_title = slug.replace("-", " ").strip().title()
                yield Article(
                    url=article_url,
                    canonical_url=canonical,
                    title=temp_title or "YourStory Funding Report",
                    source_id=self.SOURCE_ID,
                    source_name=self.SOURCE_NAME,
                    published_at=pub_dt,
                    feed_url=sm_url,
                    discovery_query="sitemap_slug",
                    extraction_status=ExtractionStatus.PENDING,
                )
