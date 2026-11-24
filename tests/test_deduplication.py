"""
tests/test_deduplication.py
============================
Unit tests for Milestone 2 deduplication, query builder, and collector.

All tests use fixtures or mocks — no live HTTP calls.
"""

from __future__ import annotations

import sys
import os
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sources.base import Article, ExtractionStatus, SourceHealth
from discovery.article_deduplicator import ArticleDeduplicator, DeduplicationStats, _normalize_title
from discovery.query_builder import QueryBuilder, SearchQuery, QueryType
from discovery.collector import DiscoveryCollector, DiscoveryResult, SourceResult

START = date(2024, 11, 23)
END = date(2026, 11, 23)


# ===========================================================================
# Helpers
# ===========================================================================

def _article(
    url: str,
    title: str = "Test Article",
    full_text: str | None = None,
    published_at: datetime | None = None,
) -> Article:
    return Article(
        url=url,
        title=title,
        source_id="test",
        source_name="Test",
        full_text=full_text,
        published_at=published_at or datetime(2025, 6, 1, tzinfo=timezone.utc),
    )


# ===========================================================================
# ArticleDeduplicator – URL deduplication
# ===========================================================================

class TestURLDeduplication:

    def test_unique_url_accepted(self):
        dedup = ArticleDeduplicator()
        a = _article("https://example.com/article-one/")
        assert dedup.is_unique(a) is True

    def test_duplicate_url_rejected(self):
        dedup = ArticleDeduplicator()
        a1 = _article("https://example.com/article/")
        a2 = _article("https://example.com/article/")
        assert dedup.is_unique(a1) is True
        assert dedup.is_unique(a2) is False

    def test_tracking_param_duplicate_rejected(self):
        """Same article with different tracking params → duplicate."""
        dedup = ArticleDeduplicator()
        a1 = _article("https://example.com/story/?utm_source=twitter")
        a2 = _article("https://example.com/story/?utm_source=newsletter")
        assert dedup.is_unique(a1) is True
        assert dedup.is_unique(a2) is False

    def test_different_articles_both_accepted(self):
        dedup = ArticleDeduplicator()
        a1 = _article("https://example.com/article-one/")
        a2 = _article("https://example.com/article-two/")
        assert dedup.is_unique(a1) is True
        assert dedup.is_unique(a2) is True

    def test_add_many_deduplicates(self):
        dedup = ArticleDeduplicator()
        articles = [
            _article("https://example.com/a/"),
            _article("https://example.com/a/"),  # duplicate
            _article("https://example.com/b/"),
        ]
        unique = dedup.add_many(articles)
        assert len(unique) == 2

    def test_stats_url_duplicate_counted(self):
        dedup = ArticleDeduplicator()
        dedup.is_unique(_article("https://example.com/a/"))
        dedup.is_unique(_article("https://example.com/a/"))
        assert dedup.stats.url_duplicates == 1
        assert dedup.stats.accepted == 1
        assert dedup.stats.total_seen == 2


# ===========================================================================
# ArticleDeduplicator – Content-hash deduplication
# ===========================================================================

class TestContentHashDeduplication:

    def test_same_content_different_url_rejected(self):
        """Same article text, different URL → content hash duplicate."""
        dedup = ArticleDeduplicator(enable_title_dedup=False)
        text = "WealthAI raises $10M Series A for private market analytics."
        a1 = _article("https://source1.com/story/", full_text=text)
        a2 = _article("https://source2.com/story/", full_text=text)
        assert dedup.is_unique(a1) is True
        assert dedup.is_unique(a2) is False

    def test_different_content_same_url_prefix_both_accepted(self):
        """Different text, different URLs → both accepted."""
        dedup = ArticleDeduplicator(enable_title_dedup=False)
        a1 = _article("https://example.com/a/", full_text="Article one content.")
        a2 = _article("https://example.com/b/", full_text="Article two content.")
        assert dedup.is_unique(a1) is True
        assert dedup.is_unique(a2) is True

    def test_no_text_articles_not_hash_rejected(self):
        """Articles without full_text have no hash → not hash-deduplicated."""
        dedup = ArticleDeduplicator(enable_title_dedup=False)
        a1 = _article("https://example.com/x/")
        a2 = _article("https://example.com/y/")  # no text, different URL
        assert dedup.is_unique(a1) is True
        assert dedup.is_unique(a2) is True  # Different URL, no hash to match


# ===========================================================================
# ArticleDeduplicator – Title-similarity deduplication
# ===========================================================================

class TestTitleDeduplication:

    def test_exact_title_duplicate_rejected(self):
        dedup = ArticleDeduplicator(title_similarity_threshold=90.0)
        a1 = _article("https://source1.com/a/", title="WealthAI raises $10M Series A")
        a2 = _article("https://source2.com/b/", title="WealthAI raises $10M Series A")
        assert dedup.is_unique(a1) is True
        assert dedup.is_unique(a2) is False

    def test_very_similar_title_rejected(self):
        dedup = ArticleDeduplicator(title_similarity_threshold=90.0)
        a1 = _article("https://s1.com/a/", title="WealthAI raises $10M Series A funding round")
        a2 = _article("https://s2.com/b/", title="WealthAI raises $10M in Series A round")
        assert dedup.is_unique(a1) is True
        assert dedup.is_unique(a2) is False

    def test_different_companies_both_accepted(self):
        dedup = ArticleDeduplicator(title_similarity_threshold=90.0)
        a1 = _article("https://s1.com/a/", title="AlphaWealth raises $10M Series A for portfolio management")
        a2 = _article("https://s2.com/b/", title="BetaFunds raises $15M Series B for private credit platform")
        assert dedup.is_unique(a1) is True
        assert dedup.is_unique(a2) is True

    def test_short_title_not_title_deduplicated(self):
        """Titles shorter than 20 chars are not title-deduplicated (too risky)."""
        dedup = ArticleDeduplicator(title_similarity_threshold=90.0)
        a1 = _article("https://s1.com/a/", title="Series A round")  # < 20 chars
        a2 = _article("https://s2.com/b/", title="Series A round")  # < 20 chars
        assert dedup.is_unique(a1) is True
        # Different URL, short title → title dedup skipped, URL dedup passes
        assert dedup.is_unique(a2) is True

    def test_title_dedup_can_be_disabled(self):
        dedup = ArticleDeduplicator(enable_title_dedup=False)
        a1 = _article("https://s1.com/a/", title="WealthAI raises $10M Series A funding round")
        a2 = _article("https://s2.com/b/", title="WealthAI raises $10M Series A funding round")
        assert dedup.is_unique(a1) is True
        assert dedup.is_unique(a2) is True  # title dedup disabled; different URLs


# ===========================================================================
# ArticleDeduplicator – Checkpoint persistence
# ===========================================================================

class TestDeduplicatorCheckpoint:

    def test_save_and_load_checkpoint(self, tmp_path):
        checkpoint_file = tmp_path / "dedup.json"
        dedup1 = ArticleDeduplicator(checkpoint_path=checkpoint_file)
        a = _article("https://example.com/article/")
        dedup1.is_unique(a)
        dedup1.save()

        # Load into a new deduplicator
        dedup2 = ArticleDeduplicator(checkpoint_path=checkpoint_file)
        dedup2.load()
        # The URL should already be known
        a2 = _article("https://example.com/article/")
        assert dedup2.is_unique(a2) is False

    def test_missing_checkpoint_file_handled_gracefully(self, tmp_path):
        missing = tmp_path / "nonexistent.json"
        dedup = ArticleDeduplicator(checkpoint_path=missing)
        dedup.load()  # Must not raise
        assert len(dedup) == 0

    def test_reset_clears_state(self):
        dedup = ArticleDeduplicator()
        dedup.is_unique(_article("https://example.com/x/"))
        assert len(dedup) == 1
        dedup.reset()
        assert len(dedup) == 0

    def test_stats_reset_on_reset(self):
        dedup = ArticleDeduplicator()
        dedup.is_unique(_article("https://example.com/x/"))
        dedup.reset()
        assert dedup.stats.total_seen == 0


# ===========================================================================
# _normalize_title helper
# ===========================================================================

class TestNormalizeTitle:

    def test_lowercases(self):
        assert _normalize_title("WealthAI Raises $10M") == _normalize_title("wealthai raises  10m")

    def test_strips_punctuation(self):
        result = _normalize_title("WealthAI raises $10M!")
        assert "$" not in result
        assert "!" not in result

    def test_collapses_whitespace(self):
        result = _normalize_title("  WealthAI   raises   funding  ")
        assert "  " not in result


# ===========================================================================
# QueryBuilder
# ===========================================================================

class TestQueryBuilder:

    def test_builds_queries(self):
        qb = QueryBuilder()
        queries = qb.build_all()
        assert len(queries) > 0

    def test_all_queries_are_search_query_objects(self):
        qb = QueryBuilder()
        for q in qb.build_all():
            assert isinstance(q, SearchQuery)

    def test_queries_are_unique(self):
        qb = QueryBuilder()
        queries = qb.build_all()
        texts = [q.text.lower() for q in queries]
        assert len(texts) == len(set(texts)), "Query texts must be unique"

    def test_tier1_queries_have_both_keywords(self):
        """Tier 1 queries must reference both a business category and a funding event."""
        qb = QueryBuilder(
            business_keywords=["wealth management"],
            funding_keywords=["Series A"],
        )
        queries = qb.build_all()
        tier1 = [q for q in queries if q.priority == 2]
        assert len(tier1) >= 1
        assert all(q.business_category is not None for q in tier1)
        assert all(q.funding_keyword is not None for q in tier1)

    def test_tier2_queries_have_geo_qualifier(self):
        qb = QueryBuilder()
        queries = qb.build_all()
        tier2 = [q for q in queries if q.priority == 3]
        assert len(tier2) > 0
        assert all(q.geo_qualifier is not None for q in tier2)

    def test_country_filtered_queries(self):
        qb = QueryBuilder()
        india_queries = qb.build_for_country("India")
        # All queries should be for India or country-agnostic
        for q in india_queries:
            assert q.country in ("India", None)

    def test_max_queries_respected(self):
        qb = QueryBuilder()
        queries = qb.build_all(max_queries=10)
        assert len(queries) <= 10

    def test_stage_specific_queries(self):
        qb = QueryBuilder()
        queries = qb.build_stage_specific("Series A")
        assert len(queries) > 0
        for q in queries:
            assert "Series A" in q.text

    def test_rss_queries_have_correct_type(self):
        qb = QueryBuilder()
        rss_queries = qb.build_for_rss()
        for q in rss_queries:
            assert q.query_type == QueryType.RSS_SEARCH

    def test_query_id_is_stable(self):
        qb = QueryBuilder(
            business_keywords=["wealth management"],
            funding_keywords=["Series A"],
        )
        queries1 = qb.build_all()
        qb2 = QueryBuilder(
            business_keywords=["wealth management"],
            funding_keywords=["Series A"],
        )
        queries2 = qb2.build_all()
        assert queries1[0].query_id == queries2[0].query_id

    def test_build_all_called_twice_gives_same_count(self):
        """build_all must reset internal state so repeated calls give same results."""
        qb = QueryBuilder()
        c1 = len(qb.build_all())
        c2 = len(qb.build_all())
        assert c1 == c2

    def test_summary_string_contains_total(self):
        qb = QueryBuilder()
        s = qb.summary()
        assert "total queries" in s


# ===========================================================================
# SearchQuery
# ===========================================================================

class TestSearchQuery:

    def test_str_returns_text(self):
        q = SearchQuery(
            text="private equity Series A",
            query_type=QueryType.RSS_SEARCH,
        )
        assert str(q) == "private equity Series A"

    def test_query_id_is_12_chars(self):
        q = SearchQuery(
            text="wealth management funding",
            query_type=QueryType.RSS_SEARCH,
        )
        assert len(q.query_id) == 12

    def test_different_texts_different_ids(self):
        q1 = SearchQuery(text="private equity", query_type=QueryType.RSS_SEARCH)
        q2 = SearchQuery(text="wealth management", query_type=QueryType.RSS_SEARCH)
        assert q1.query_id != q2.query_id


# ===========================================================================
# DiscoveryCollector (mocked)
# ===========================================================================

class TestDiscoveryCollector:

    def _make_mock_source_class(self, source_id: str, articles: list[Article], fail: bool = False):
        """Create a fake source class that returns predefined articles."""
        health = SourceHealth(source_id=source_id)
        if fail:
            health.record_error("Simulated failure")
        health.articles_found = len(articles)
        health.finish()

        class MockSource:
            SOURCE_ID = source_id
            SOURCE_NAME = f"Mock {source_id}"

            def __init__(self, start_date=None, end_date=None, **kwargs):
                pass

            def run(self):
                if fail:
                    raise RuntimeError("Simulated catastrophic source failure")
                return articles, health

        return MockSource

    def test_collector_runs_sources_and_returns_result(self):
        articles = [
            _article("https://example.com/a/", title="WealthAI raises $10M Series A"),
            _article("https://example.com/b/", title="PortfolioOS secures $5M seed"),
        ]
        MockCls = self._make_mock_source_class("mock_source", articles)

        collector = DiscoveryCollector(
            start_date=START,
            end_date=END,
            incremental=False,
        )

        with patch("discovery.collector.get_all_sources", return_value=[MockCls]):
            with patch("discovery.collector.get_source", return_value=MockCls):
                result = collector.run()

        assert isinstance(result, DiscoveryResult)
        assert result.total_unique == 2
        assert result.total_discovered == 2

    def test_collector_deduplicates_across_sources(self):
        """The same article from two different sources → deduplicated to one."""
        shared_url = "https://example.com/shared/"
        article_s1 = _article(shared_url, title="WealthAI raises $10M in Series A round")
        article_s2 = _article(shared_url, title="WealthAI raises $10M in Series A round")

        Mock1 = self._make_mock_source_class("source_1", [article_s1])
        Mock2 = self._make_mock_source_class("source_2", [article_s2])

        collector = DiscoveryCollector(
            start_date=START, end_date=END, incremental=False
        )
        with patch("discovery.collector.get_all_sources", return_value=[Mock1, Mock2]):
            result = collector.run()

        assert result.total_unique == 1
        assert result.total_duplicate >= 1

    def test_failed_source_does_not_stop_pipeline(self):
        """A source that raises must not prevent other sources from running."""
        good_articles = [_article("https://example.com/good/")]
        GoodCls = self._make_mock_source_class("good_source", good_articles)

        # Create a source that always raises
        class BombSource:
            SOURCE_ID = "bomb_source"
            SOURCE_NAME = "Bomb Source"

            def __init__(self, **kwargs):
                pass

            def run(self):
                raise RuntimeError("Kaboom!")

        collector = DiscoveryCollector(
            start_date=START, end_date=END, incremental=False
        )
        with patch("discovery.collector.get_all_sources", return_value=[GoodCls, BombSource]):
            result = collector.run()

        # Good source still produced its article
        assert result.total_unique >= 1

    def test_collector_respects_source_id_filter(self):
        a1 = [_article("https://example.com/tc/")]
        a2 = [_article("https://example.com/inc/")]
        TCCls = self._make_mock_source_class("techcrunch", a1)
        Inc42Cls = self._make_mock_source_class("inc42", a2)

        collector = DiscoveryCollector(
            start_date=START, end_date=END,
            source_ids=["techcrunch"],
            incremental=False,
        )
        with patch("discovery.collector.get_all_sources", return_value=[TCCls, Inc42Cls]):
            with patch("discovery.collector.get_source", side_effect=lambda sid: TCCls if sid == "techcrunch" else None):
                result = collector.run()

        assert result.total_unique == 1

    def test_discovery_result_has_correct_date_range(self):
        collector = DiscoveryCollector(
            start_date=START, end_date=END, incremental=False
        )
        with patch("discovery.collector.get_all_sources", return_value=[]):
            result = collector.run()
        assert result.start_date == START
        assert result.end_date == END

    def test_discovery_result_to_dict(self):
        result = DiscoveryResult(start_date=START, end_date=END)
        result.finish()
        d = result.to_dict()
        assert "start_date" in d
        assert "end_date" in d
        assert "total_unique" in d
        assert d["start_date"] == str(START)

    def test_incremental_skips_known_urls(self, tmp_path):
        """Articles in the checkpoint should be skipped on second run."""
        checkpoint_path = tmp_path / "checkpoint.json"
        dedup_path = tmp_path / "dedup.json"

        articles = [_article("https://example.com/known/")]
        MockCls = self._make_mock_source_class("mock", articles)

        # First run – discovers the article
        collector1 = DiscoveryCollector(
            start_date=START, end_date=END,
            checkpoint_path=checkpoint_path,
            dedup_checkpoint_path=dedup_path,
            incremental=True,
        )
        with patch("discovery.collector.get_all_sources", return_value=[MockCls]):
            result1 = collector1.run()
        assert result1.total_unique == 1

        # Second run – same article should be skipped
        MockCls2 = self._make_mock_source_class("mock", articles)
        collector2 = DiscoveryCollector(
            start_date=START, end_date=END,
            checkpoint_path=checkpoint_path,
            dedup_checkpoint_path=dedup_path,
            incremental=True,
        )
        with patch("discovery.collector.get_all_sources", return_value=[MockCls2]):
            result2 = collector2.run()
        assert result2.total_unique == 0


# ===========================================================================
# DiscoveryResult
# ===========================================================================

class TestDiscoveryResult:

    def test_duration_seconds_computed(self):
        result = DiscoveryResult(start_date=START, end_date=END)
        result.finish()
        assert result.duration_seconds >= 0.0

    def test_unfinished_result_duration_is_zero(self):
        result = DiscoveryResult(start_date=START, end_date=END)
        assert result.duration_seconds == 0.0

    def test_print_summary_does_not_raise(self, capsys):
        result = DiscoveryResult(start_date=START, end_date=END)
        health = SourceHealth(source_id="test")
        health.finish()
        result.source_results = [SourceResult(source_id="test", articles=[], health=health)]
        result.finish()
        result.print_summary()
        captured = capsys.readouterr()
        assert "DISCOVERY SUMMARY" in captured.out
