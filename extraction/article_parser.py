"""
extraction/article_parser.py
============================
Article content extraction engine using Trafilatura and BeautifulSoup.

Features:
- Primary extraction via Trafilatura (state-of-the-art web article text extractor).
- Fallback extraction via BeautifulSoup for edge cases or non-standard HTML.
- Extracts article body, title, author, publication date, and metadata.
- Handles redirects, timeouts, encoding issues, and HTTP errors gracefully.
- Supports offline HTML extraction for testing and reproducible reprocessing.
- Computes SHA-256 content hashes and updates Article extraction status.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional
from bs4 import BeautifulSoup
import trafilatura
from dateutil import parser as dateutil_parser

from sources.base import Article, ExtractionStatus, build_session, canonicalize_url
from config.settings import USER_AGENT, REQUEST_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)


class ArticleParser:
    """
    Fetches and parses full article content from web pages or raw HTML.
    """

    def __init__(
        self,
        user_agent: str = USER_AGENT,
        timeout: int = REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        self.user_agent = user_agent
        self.timeout = timeout
        self._session = None

    @property
    def session(self):
        if self._session is None:
            self._session = build_session(user_agent=self.user_agent, timeout=self.timeout)
        return self._session

    def fetch_html(self, url: str) -> tuple[Optional[str], Optional[str]]:
        """
        Fetch HTML from URL with redirect following.
        Returns (html_content, final_url).
        """
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        try:
            resp = self.session.get(url, headers=headers, timeout=self.timeout)
            if resp.status_code == 200:
                final_url = canonicalize_url(resp.url)
                return resp.text, final_url
            logger.warning("HTTP %d when fetching %s", resp.status_code, url)
        except Exception as exc:
            logger.warning("Failed to fetch %s: %s", url, exc)
        return None, None

    def parse_html(
        self,
        html_content: str,
        url: str = "",
        existing_article: Optional[Article] = None,
    ) -> Article:
        """
        Extract clean text and metadata from raw HTML content.
        Uses Trafilatura first, falling back to BeautifulSoup.
        """
        if not html_content or not html_content.strip():
            if existing_article:
                existing_article.extraction_status = ExtractionStatus.FAILED
                return existing_article
            return Article(
                url=url,
                title="",
                source_id="unknown",
                source_name="Unknown",
                extraction_status=ExtractionStatus.FAILED,
            )

        # 1. Primary extraction with Trafilatura
        body_text = trafilatura.extract(
            html_content,
            include_comments=False,
            include_tables=True,
            no_fallback=False,
            url=url,
        )

        # 2. Extract metadata via BeautifulSoup
        soup = BeautifulSoup(html_content, "html.parser")

        # Fallback body extraction if Trafilatura fails
        if not body_text or len(body_text.strip()) < 50:
            article_tag = soup.find("article") or soup.find("main") or soup.find(class_=lambda c: c and "post-content" in c)
            if article_tag:
                paras = [p.get_text().strip() for p in article_tag.find_all("p") if p.get_text().strip()]
                body_text = "\n\n".join(paras)
            else:
                paras = [p.get_text().strip() for p in soup.find_all("p") if len(p.get_text().strip()) > 30]
                body_text = "\n\n".join(paras)

        # Title extraction
        title = ""
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()
        elif soup.title and soup.title.string:
            title = soup.title.string.strip()

        # Author extraction
        author = None
        author_meta = soup.find("meta", attrs={"name": "author"}) or soup.find("meta", property="article:author")
        if author_meta and author_meta.get("content"):
            author = author_meta["content"].strip()

        # Date extraction (meta tags, JSON-LD, <time>, URL path)
        published_at = None
        for time_meta in (
            soup.find("meta", property="article:published_time"),
            soup.find("meta", property="og:updated_time"),
            soup.find("meta", itemprop="datePublished"),
            soup.find("meta", attrs={"name": "pubdate"}),
            soup.find("meta", attrs={"name": "publishdate"}),
            soup.find("meta", attrs={"name": "DC.date.issued"}),
        ):
            if time_meta and time_meta.get("content"):
                try:
                    dt = dateutil_parser.parse(time_meta["content"])
                    published_at = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
                    break
                except Exception:
                    pass

        if published_at is None:
            for script in soup.find_all("script", type="application/ld+json"):
                raw_json = script.string or ""
                m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', raw_json)
                if m:
                    try:
                        dt = dateutil_parser.parse(m.group(1))
                        published_at = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
                        break
                    except Exception:
                        pass

        if published_at is None:
            time_el = soup.find("time", datetime=True)
            if time_el:
                try:
                    dt = dateutil_parser.parse(time_el["datetime"])
                    published_at = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
                except Exception:
                    pass

        # Soft-404 / generic SPA shell guard
        if body_text and len(body_text.strip()) < 150 and "stories about startups & entrepreneurships" in (title or "").lower():
            body_text = ""

        # Update or construct Article
        if existing_article:
            if body_text and len(body_text.strip()) >= 50:
                existing_article.full_text = body_text.strip()
                existing_article.extraction_status = ExtractionStatus.SUCCESS
            else:
                existing_article.extraction_status = ExtractionStatus.FAILED

            if title and (not existing_article.title or existing_article.discovery_query == "sitemap_slug"):
                existing_article.title = title
            if not existing_article.author and author:
                existing_article.author = author
            if published_at and (not existing_article.published_at or existing_article.discovery_query == "sitemap_slug"):
                existing_article.published_at = published_at

            # Recompute content hash
            existing_article.compute_content_hash()
            return existing_article

        return Article(
            url=url,
            title=title or "Untitled",
            source_id="parsed_html",
            source_name="Parsed HTML",
            full_text=body_text.strip() if body_text else None,
            author=author,
            published_at=published_at,
            extraction_status=ExtractionStatus.SUCCESS if body_text else ExtractionStatus.FAILED,
        )

    def extract_article(self, article: Article) -> Article:
        """
        Fetch HTML from the article's URL and populate its full_text and metadata.
        """
        html, final_url = self.fetch_html(article.url)
        if not html:
            article.extraction_status = ExtractionStatus.FAILED
            return article

        if final_url and final_url != article.url:
            article.canonical_url = final_url

        return self.parse_html(html, url=article.url, existing_article=article)
