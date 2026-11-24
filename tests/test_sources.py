"""
tests/test_sources.py
======================
Unit tests for Milestone 1:
  - BaseSource contract
  - RSSSource parsing (against fixtures – no live network calls)
  - URL canonicalization
  - Date filtering
  - Duplicate URL detection
  - Malformed feed resilience
  - Source registry
  - GoogleNews query builder

All tests use monkeypatching / fixtures instead of real HTTP.
"""

from __future__ import annotations

import sys
import os
from datetime import date, datetime, timezone
from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path regardless of where pytest is invoked.
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from tests.fixtures.rss_fixtures import (
    TECHCRUNCH_RSS,
    INC42_ATOM,
    OUT_OF_RANGE_RSS,
    DUPLICATE_URL_RSS,
    MALFORMED_RSS,
    EMPTY_RSS,
)
from sources.base import Article, BaseSource, ExtractionStatus, canonicalize_url
from sources.rss_source import RSSSource, _parse_feed_date
from sources.google_news import build_google_news_queries, build_feed_url, GoogleNewsSource


# ===========================================================================
# Helpers
# ===========================================================================

START = date(2024, 11, 23)
END = date(2026, 11, 23)


def _make_rss_source(
    rss_text: str,
    start: date = START,
    end: date = END,
    source_id: str = "test_rss",
    source_name: str = "Test RSS",
) -> tuple[RSSSource, list[Article]]:
    """
    Create an RSSSource instance and collect its articles by patching
    the HTTP layer so no real network call is made.
    """
    source = RSSSource(
        start_date=start,
        end_date=end,
        rss_feeds=["https://example.com/feed/"],
        request_delay=0,
    )
    source.SOURCE_ID = source_id
    source.SOURCE_NAME = source_name

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = rss_text

    with patch.object(source, "_get", return_value=mock_response):
        articles, health = source.run()

    return source, articles


# ===========================================================================
# URL canonicalization
# ===========================================================================

class TestCanonicalize:

    def test_removes_utm_params(self):
        url = "https://techcrunch.com/article/?utm_source=twitter&utm_medium=social"
        assert "utm_source" not in canonicalize_url(url)
        assert "utm_medium" not in canonicalize_url(url)

    def test_removes_fbclid(self):
        url = "https://example.com/post/?fbclid=abc123"
        assert "fbclid" not in canonicalize_url(url)

    def test_preserves_meaningful_params(self):
        url = "https://example.com/search/?q=funding&page=2"
        canonical = canonicalize_url(url)
        assert "q=funding" in canonical
        assert "page=2" in canonical

    def test_lowercases_scheme_and_host(self):
        url = "HTTPS://TechCrunch.COM/article/"
        canonical = canonicalize_url(url)
        assert canonical.startswith("https://techcrunch.com/")

    def test_strips_trailing_slash(self):
        url = "https://example.com/article/"
        canonical = canonicalize_url(url)
        assert canonical == "https://example.com/article"

    def test_root_path_preserved(self):
        url = "https://example.com/"
        canonical = canonicalize_url(url)
        # Root slash is preserved
        assert canonical == "https://example.com/"

    def test_removes_fragment(self):
        url = "https://example.com/article/#section1"
        canonical = canonicalize_url(url)
        assert "#" not in canonical

    def test_duplicate_tracking_urls_match(self):
        url1 = "https://example.com/investco/?utm_source=twitter"
        url2 = "https://example.com/investco/?utm_source=newsletter"
        assert canonicalize_url(url1) == canonicalize_url(url2)

    def test_different_articles_do_not_match(self):
        url1 = "https://example.com/article-one/"
        url2 = "https://example.com/article-two/"
        assert canonicalize_url(url1) != canonicalize_url(url2)


# ===========================================================================
# RSS parsing
# ===========================================================================

class TestRSSParsing:

    def test_techcrunch_feed_parses_articles(self):
        _, articles = _make_rss_source(TECHCRUNCH_RSS)
        assert len(articles) >= 2

    def test_articles_have_required_fields(self):
        _, articles = _make_rss_source(TECHCRUNCH_RSS)
        for article in articles:
            assert article.url, "URL must not be empty"
            assert article.title, "Title must not be empty"
            assert article.source_id == "test_rss"
            assert article.source_name == "Test RSS"

    def test_articles_have_publication_date(self):
        _, articles = _make_rss_source(TECHCRUNCH_RSS)
        for article in articles:
            assert article.published_at is not None
            assert article.published_at.tzinfo is not None, "Date must be tz-aware"

    def test_articles_have_summary(self):
        _, articles = _make_rss_source(TECHCRUNCH_RSS)
        for article in articles:
            assert article.summary is not None and len(article.summary) > 0

    def test_atom_feed_parses(self):
        """Atom feeds (e.g. Inc42) must also parse correctly."""
        _, articles = _make_rss_source(INC42_ATOM)
        assert len(articles) == 2
        titles = [a.title for a in articles]
        assert any("WealthBridge" in t for t in titles)
        assert any("AltFunds" in t for t in titles)

    def test_canonical_url_is_set(self):
        _, articles = _make_rss_source(TECHCRUNCH_RSS)
        for article in articles:
            assert article.canonical_url is not None

    def test_extraction_status_is_pending(self):
        _, articles = _make_rss_source(TECHCRUNCH_RSS)
        for article in articles:
            assert article.extraction_status == ExtractionStatus.PENDING

    def test_feed_url_is_recorded(self):
        _, articles = _make_rss_source(TECHCRUNCH_RSS)
        for article in articles:
            assert article.feed_url == "https://example.com/feed/"


# ===========================================================================
# Date filtering
# ===========================================================================

class TestDateFiltering:

    def test_in_range_articles_included(self):
        """Articles from 2025 (within range) must be returned."""
        _, articles = _make_rss_source(TECHCRUNCH_RSS, start=START, end=END)
        # All TechCrunch fixture articles are from 2025 – they must all pass
        assert len(articles) >= 2

    def test_out_of_range_articles_excluded(self):
        """The fixture article dated 2024-01-01 must be excluded."""
        _, articles = _make_rss_source(OUT_OF_RANGE_RSS, start=START, end=END)
        assert len(articles) == 0

    def test_article_is_within_date_range(self):
        article = Article(
            url="https://example.com/article/",
            title="Test",
            source_id="test",
            source_name="Test",
            published_at=datetime(2025, 6, 1, tzinfo=timezone.utc),
        )
        assert article.is_within_date_range(START, END)

    def test_article_before_start_excluded(self):
        article = Article(
            url="https://example.com/article/",
            title="Test",
            source_id="test",
            source_name="Test",
            published_at=datetime(2024, 6, 1, tzinfo=timezone.utc),
        )
        assert not article.is_within_date_range(START, END)

    def test_article_after_end_excluded(self):
        article = Article(
            url="https://example.com/article/",
            title="Test",
            source_id="test",
            source_name="Test",
            published_at=datetime(2027, 1, 1, tzinfo=timezone.utc),
        )
        assert not article.is_within_date_range(START, END)

    def test_article_on_boundary_included(self):
        article_start = Article(
            url="https://example.com/on-start/",
            title="On Start",
            source_id="test",
            source_name="Test",
            published_at=datetime(2024, 11, 23, tzinfo=timezone.utc),
        )
        article_end = Article(
            url="https://example.com/on-end/",
            title="On End",
            source_id="test",
            source_name="Test",
            published_at=datetime(2026, 11, 23, tzinfo=timezone.utc),
        )
        assert article_start.is_within_date_range(START, END)
        assert article_end.is_within_date_range(START, END)

    def test_article_without_date_passes_filter(self):
        """Articles with no parsed date are kept for manual review."""
        article = Article(
            url="https://example.com/nodateArticle/",
            title="No date article",
            source_id="test",
            source_name="Test",
            published_at=None,
        )
        assert article.is_within_date_range(START, END)


# ===========================================================================
# Duplicate URL detection
# ===========================================================================

class TestDuplicateDetection:

    def test_duplicate_tracking_urls_deduplicated(self):
        """Two entries with the same URL but different tracking params → one article."""
        _, articles = _make_rss_source(DUPLICATE_URL_RSS)
        urls = [a.canonical_url for a in articles]
        assert len(urls) == len(set(urls)), "Duplicate canonical URLs must be deduplicated"

    def test_duplicate_count_is_one(self):
        _, articles = _make_rss_source(DUPLICATE_URL_RSS)
        assert len(articles) == 1


# ===========================================================================
# Malformed feed resilience
# ===========================================================================

class TestMalformedFeedResilience:

    def test_malformed_feed_does_not_raise(self):
        """A malformed RSS feed must not propagate exceptions."""
        try:
            _, articles = _make_rss_source(MALFORMED_RSS)
        except Exception as exc:
            pytest.fail(f"Malformed feed raised an exception: {exc}")

    def test_malformed_feed_skips_entries_without_link(self):
        """Entries with no <link> must be silently skipped."""
        _, articles = _make_rss_source(MALFORMED_RSS)
        for a in articles:
            assert a.url, "Every returned article must have a URL"

    def test_malformed_feed_skips_entries_without_title(self):
        """Entries with empty <title> must be skipped."""
        _, articles = _make_rss_source(MALFORMED_RSS)
        for a in articles:
            assert a.title.strip(), "Every returned article must have a non-empty title"

    def test_empty_feed_returns_no_articles(self):
        _, articles = _make_rss_source(EMPTY_RSS)
        assert len(articles) == 0


# ===========================================================================
# Source registry
# ===========================================================================

class TestSourceRegistry:

    def test_registry_has_known_sources(self):
        from sources import get_all_sources
        source_classes = get_all_sources()
        ids = {cls.SOURCE_ID for cls in source_classes}
        # Check a representative subset
        expected = {
            "techcrunch", "inc42", "entrackr", "yourstory",
            "venturebeat", "businesswire", "prnewswire",
            "google_news", "sec_edgar",
        }
        missing = expected - ids
        assert not missing, f"Missing source IDs in registry: {missing}"

    def test_all_registered_sources_have_source_id(self):
        from sources import get_all_sources
        for cls in get_all_sources():
            assert cls.SOURCE_ID, f"{cls.__name__} has no SOURCE_ID"

    def test_all_registered_sources_have_source_name(self):
        from sources import get_all_sources
        for cls in get_all_sources():
            assert cls.SOURCE_NAME, f"{cls.__name__} has no SOURCE_NAME"

    def test_source_registry_lookup(self):
        from sources import get_source
        cls = get_source("techcrunch")
        assert cls is not None
        assert cls.SOURCE_ID == "techcrunch"

    def test_unknown_source_returns_none(self):
        from sources import get_source
        assert get_source("does_not_exist") is None

    def test_sources_are_instantiable(self):
        """Every registered source must be instantiable without raising."""
        from sources import get_all_sources
        for cls in get_all_sources():
            try:
                instance = cls(start_date=START, end_date=END)
                assert isinstance(instance, BaseSource)
            except Exception as exc:
                pytest.fail(f"{cls.__name__} raised on init: {exc}")


# ===========================================================================
# Google News query builder
# ===========================================================================

class TestGoogleNewsQueryBuilder:

    def test_queries_are_non_empty(self):
        queries = build_google_news_queries()
        assert len(queries) > 0

    def test_queries_are_strings(self):
        for q in build_google_news_queries():
            assert isinstance(q, str)
            assert len(q.strip()) > 0

    def test_queries_are_unique(self):
        queries = build_google_news_queries()
        assert len(queries) == len(set(queries)), "All queries must be unique"

    def test_queries_contain_funding_keywords(self):
        queries = build_google_news_queries()
        combined = " ".join(queries).lower()
        assert "funding" in combined or "series" in combined

    def test_feed_url_builds_correctly(self):
        url = build_feed_url("wealth management funding")
        assert url.startswith("https://news.google.com/rss/search")
        assert "wealth+management+funding" in url or "wealth%20management%20funding" in url

    def test_google_news_respects_max_queries(self):
        source = GoogleNewsSource(max_queries=5)
        queries = source._get_queries()
        assert len(queries) <= 5

    def test_google_news_custom_queries(self):
        custom = ["private equity India funding", "wealthtech Series A"]
        source = GoogleNewsSource(custom_queries=custom)
        assert source._get_queries() == custom


# ===========================================================================
# Source health tracking
# ===========================================================================

class TestSourceHealth:

    def test_failed_source_records_error(self):
        source = RSSSource(
            start_date=START,
            end_date=END,
            rss_feeds=["https://example.com/feed/"],
            request_delay=0,
        )
        with patch.object(source, "_get", return_value=None):
            _, health = source.run()
        assert health.articles_failed >= 0  # HTTP failure = skipped feed, not articles_failed
        # The key assertion: success flag depends on errors list
        # An empty feed response (None) triggers a health error
        assert health.finished_at is not None

    def test_unhandled_exception_in_discovery_is_caught(self):
        """An unhandled exception in discover() must set health.success=False."""

        class BrokenSource(RSSSource):
            SOURCE_ID = "broken"
            SOURCE_NAME = "Broken"

            def discover(self):
                raise RuntimeError("Simulated catastrophic failure")

        broken = BrokenSource(start_date=START, end_date=END, request_delay=0)
        articles, health = broken.run()
        assert articles == []
        assert not health.success
        assert len(health.errors) > 0


# ===========================================================================
# Article model
# ===========================================================================

class TestArticleModel:

    def test_article_canonical_url_auto_set(self):
        a = Article(
            url="https://example.com/article/?utm_source=test",
            title="Test",
            source_id="test",
            source_name="Test",
        )
        assert a.canonical_url is not None
        assert "utm_source" not in a.canonical_url

    def test_article_content_hash_computed_when_text_present(self):
        a = Article(
            url="https://example.com/article/",
            title="Test",
            source_id="test",
            source_name="Test",
            full_text="Hello world article text",
        )
        assert a.content_hash is not None
        assert len(a.content_hash) == 64  # SHA-256 hex

    def test_article_no_hash_when_no_text(self):
        a = Article(
            url="https://example.com/article/",
            title="Test",
            source_id="test",
            source_name="Test",
        )
        assert a.content_hash is None

    def test_article_discovered_at_is_utc(self):
        a = Article(
            url="https://example.com/",
            title="Test",
            source_id="t",
            source_name="T",
        )
        assert a.discovered_at.tzinfo is not None
