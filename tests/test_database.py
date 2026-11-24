"""
tests/test_database.py
======================
Unit tests for database persistence, entity resolution, and funding round deduplication.

Tests cover:
- Database repository operations with SQLite in-memory
- Foreign keys, relationships, and evidence linkage
- Company normalization and legal suffix stripping
- Entity resolution (domain matching, normalized name matching, fuzzy matching)
- Funding round deduplication across multiple reports
- Multi-round handling (Seed vs Series A for the same company)
- Data validation rules
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import pytest

from database.models import Company, FundingRound, Article as DBArticle, Evidence
from database.repository import DatabaseRepository
from processing.normalizer import normalize_company_name, extract_website_domain
from processing.entity_resolution import CompanyEntityResolver
from processing.deduplicator import FundingRoundDeduplicator
from processing.validator import validate_funding_round


@pytest.fixture
def repo():
    # Use isolated in-memory SQLite database for tests
    return DatabaseRepository(db_url="sqlite:///:memory:")


class TestDatabaseRepository:

    def test_save_and_get_company(self, repo):
        comp = Company(
            canonical_name="WealthAI",
            normalized_name="wealthai",
            website="https://wealthai.io",
            website_domain="wealthai.io",
            headquarters_country="United States",
            headquarters_city="San Francisco",
            primary_category="Wealth Management",
            relevance_status="DIRECT_MATCH",
            classification_confidence=0.95,
        )
        saved = repo.save_company(comp)
        assert saved.id is not None
        assert saved.canonical_name == "WealthAI"

        fetched = repo.get_company_by_id(saved.id)
        assert fetched is not None
        assert fetched.headquarters_city == "San Francisco"

    def test_save_funding_round_and_evidence(self, repo):
        comp = repo.save_company(
            Company(
                canonical_name="WealthBridge",
                normalized_name="wealthbridge",
                headquarters_country="India",
                primary_category="Private Markets",
                relevance_status="DIRECT_MATCH",
            )
        )

        f_round = repo.save_funding_round(
            FundingRound(
                company_id=comp.id,
                funding_stage="Series B",
                amount=500_000_000.0,
                currency="INR",
                announcement_date=date(2025, 5, 1),
                lead_investor="Tiger Global",
                investors=["Tiger Global", "Peak XV"],
            )
        )
        assert f_round.id is not None

        ev = repo.save_evidence(
            field_name="funding_amount",
            evidence_text="WealthBridge raised INR 50 crore in Series B.",
            company_id=comp.id,
            funding_round_id=f_round.id,
            confidence=0.95,
        )
        assert ev.id is not None

        # Verify rounds for company
        rounds = repo.get_funding_rounds_for_company(comp.id)
        assert len(rounds) == 1
        assert rounds[0].amount == 500_000_000.0


class TestNormalizer:

    def test_legal_suffixes_stripped(self):
        assert normalize_company_name("WealthAI, Inc.") == "wealthai"
        assert normalize_company_name("WealthBridge Pvt. Ltd.") == "wealthbridge"
        assert normalize_company_name("PortfolioOS Technologies LLC") == "portfolioos"
        assert normalize_company_name("AltFunds Corporation") == "altfunds"

    def test_extract_website_domain(self):
        assert extract_website_domain("https://wealthai.io") == "wealthai.io"
        assert extract_website_domain("https://www.wealthai.io/about") == "wealthai.io"
        assert extract_website_domain("http://altassets.co.in/contact?id=1") == "altassets.co.in"
        assert extract_website_domain(None) is None


class TestEntityResolution:

    def test_resolve_exact_domain(self):
        resolver = CompanyEntityResolver()
        existing = [
            Company(
                id=1,
                canonical_name="WealthAI Inc",
                normalized_name="wealthai",
                website_domain="wealthai.io",
                headquarters_country="United States",
            )
        ]
        matched, conf, reason = resolver.resolve(
            name="WealthAI Technologies",
            website="https://www.wealthai.io/products",
            existing_companies=existing,
        )
        assert matched is not None
        assert matched.id == 1
        assert conf == 1.0

    def test_resolve_exact_normalized_name(self):
        resolver = CompanyEntityResolver()
        existing = [
            Company(
                id=2,
                canonical_name="AltFunds Platform",
                normalized_name="altfunds",
                headquarters_country="India",
            )
        ]
        matched, conf, reason = resolver.resolve(
            name="AltFunds Pvt Ltd",
            existing_companies=existing,
        )
        assert matched is not None
        assert matched.id == 2
        assert conf >= 0.95

    def test_fuzzy_name_match(self):
        resolver = CompanyEntityResolver(fuzzy_threshold=88.0)
        existing = [
            Company(
                id=3,
                canonical_name="Private Market Analytics",
                normalized_name="private market analytics",
                headquarters_country="United States",
            )
        ]
        matched, conf, reason = resolver.resolve(
            name="Private Market Analytics Platform",
            country="United States",
            existing_companies=existing,
        )
        assert matched is not None
        assert matched.id == 3

    def test_guard_against_merging_different_countries(self):
        """Two unrelated companies with the same generic name in different countries must not merge."""
        resolver = CompanyEntityResolver()
        existing = [
            Company(
                id=4,
                canonical_name="Investo",
                normalized_name="investo",
                headquarters_country="India",
            )
        ]
        matched, conf, reason = resolver.resolve(
            name="Investo",
            country="United States",  # Different country
            existing_companies=existing,
        )
        assert matched is None


class TestFundingRoundDeduplication:

    def test_same_round_reported_twice_deduplicated(self):
        """Two articles about the same round should map to the same round record."""
        dedup = FundingRoundDeduplicator()
        existing_rounds = [
            FundingRound(
                id=10,
                company_id=1,
                funding_stage="Series A",
                amount=12_500_000.0,
                currency="USD",
                announcement_date=date(2025, 3, 15),
            )
        ]

        # Second article reports the same round
        matched, reason = dedup.find_matching_round(
            company_id=1,
            stage="Series A",
            amount=12_500_000.0,
            currency="USD",
            announcement_date=date(2025, 3, 16),
            existing_rounds=existing_rounds,
        )
        assert matched is not None
        assert matched.id == 10
        assert "Matched round" in reason

    def test_distinct_rounds_for_same_company_not_merged(self):
        """Seed round and Series A for the same company must produce separate rounds."""
        dedup = FundingRoundDeduplicator()
        existing_rounds = [
            FundingRound(
                id=11,
                company_id=2,
                funding_stage="Seed",
                amount=2_000_000.0,
                currency="USD",
                announcement_date=date(2024, 12, 1),
            )
        ]

        # Same company raises Series A later
        matched, reason = dedup.find_matching_round(
            company_id=2,
            stage="Series A",
            amount=10_000_000.0,
            currency="USD",
            announcement_date=date(2025, 10, 1),
            existing_rounds=existing_rounds,
        )
        assert matched is None
        assert "Distinct funding round" in reason


class TestValidator:

    def test_valid_funding_round(self):
        res = validate_funding_round(
            company_name="WealthAI",
            amount=10_000_000.0,
            currency="USD",
            funding_stage="Series A",
        )
        assert res.is_valid is True
        assert len(res.errors) == 0

    def test_invalid_negative_amount(self):
        res = validate_funding_round(
            company_name="BadCo",
            amount=-500.0,
            currency="USD",
            funding_stage="Seed",
        )
        assert res.is_valid is False
        assert any("negative" in err for err in res.errors)
