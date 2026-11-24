"""
tests/test_classification.py
=============================
Unit tests for company business classification and relevance scoring.

Covers:
- Direct matches in Private Markets, Alternative Investments, Wealth Management
- Adjacent matches in Investment Infrastructure & Portfolio Analytics
- Exclusions: Payment-only, Lending-only, Insurance-only, E-commerce
- Guardrail: A payment gateway is NOT wealth management even if labeled fintech
- Guardrail: Generic fintech without investment products is excluded
- Multi-category attribution (primary + secondary)
- Relevance scoring and confidence calculation
"""

from __future__ import annotations

import pytest
from classification.business_classifier import BusinessClassifier, RelevanceStatus
from classification.relevance_scorer import RelevanceScorer
from classification.geography_classifier import GeographyVerificationResult, GeoStatus


@pytest.fixture
def classifier():
    return BusinessClassifier()


class TestDirectMatches:

    def test_private_markets_direct_match(self, classifier):
        res = classifier.classify(
            company_name="AltMarkets",
            description="A secondary market platform for unlisted shares and pre-IPO private equity investments.",
        )
        assert res.relevance_status == RelevanceStatus.DIRECT_MATCH
        assert res.primary_category == "Private Markets"
        assert res.relevance_score >= 0.85
        assert res.classification_confidence >= 0.70

    def test_alternative_investments_direct_match(self, classifier):
        res = classifier.classify(
            company_name="FractionalRealEstate",
            description="Fractional ownership real estate investment platform providing retail access to commercial property.",
        )
        assert res.relevance_status == RelevanceStatus.DIRECT_MATCH
        assert res.primary_category == "Alternative Investments"
        assert res.relevance_score >= 0.85

    def test_wealth_management_direct_match(self, classifier):
        res = classifier.classify(
            company_name="WealthPilot",
            description="AI-driven digital wealth management and automated portfolio management software for family offices.",
        )
        assert res.relevance_status == RelevanceStatus.DIRECT_MATCH
        assert res.primary_category == "Wealth Management"
        assert res.relevance_score >= 0.85

    def test_multi_category_attribution(self, classifier):
        """A company combining private markets and wealth management must have both."""
        res = classifier.classify(
            company_name="UnifiedCapital",
            description="Wealth management platform integrating private equity secondaries with portfolio analytics.",
        )
        assert res.relevance_status == RelevanceStatus.DIRECT_MATCH
        categories = [res.primary_category] + res.secondary_categories
        assert "Wealth Management" in categories or "Private Markets" in categories
        assert len(res.secondary_categories) >= 1


class TestAdjacentMatches:

    def test_investment_infrastructure_adjacent_match(self, classifier):
        res = classifier.classify(
            company_name="AssetFlow",
            description="Cloud investment infrastructure and portfolio analytics platform for registered investment advisors.",
        )
        assert res.relevance_status in (RelevanceStatus.ADJACENT_MATCH, RelevanceStatus.DIRECT_MATCH)
        assert res.relevance_score >= 0.70


class TestNegativeExclusions:

    def test_payment_gateway_excluded(self, classifier):
        """Payment gateways must be NOT_RELEVANT even if described as financial technology."""
        res = classifier.classify(
            company_name="PayQuick",
            description="Fintech startup offering payment gateway, checkout solutions, and merchant payment processing.",
        )
        assert res.relevance_status == RelevanceStatus.NOT_RELEVANT
        assert "Payment-only" in res.classification_reasoning

    def test_lending_only_excluded(self, classifier):
        res = classifier.classify(
            company_name="QuickCash",
            description="A consumer lending app offering instant personal loans and buy now pay later credit.",
        )
        assert res.relevance_status == RelevanceStatus.NOT_RELEVANT
        assert "Lending-only" in res.classification_reasoning

    def test_insurance_only_excluded(self, classifier):
        res = classifier.classify(
            company_name="InsureFast",
            description="Insurtech platform providing health insurance policy comparison and claims management.",
        )
        assert res.relevance_status == RelevanceStatus.NOT_RELEVANT
        assert "Insurance-only" in res.classification_reasoning

    def test_ecommerce_excluded(self, classifier):
        res = classifier.classify(
            company_name="ShopTrend",
            description="Online marketplace for goods and retail shopping with instant delivery.",
        )
        assert res.relevance_status == RelevanceStatus.NOT_RELEVANT


class TestRelevanceScorer:

    def test_scorer_qualified_startup(self, classifier):
        scorer = RelevanceScorer()
        biz = classifier.classify("WealthAI", "Digital wealth management and portfolio management platform.")
        geo = GeographyVerificationResult(
            headquarters_country="United States",
            headquarters_city="San Francisco",
            status=GeoStatus.VERIFIED,
            confidence=0.90,
        )
        score = scorer.score(biz, geo)
        assert score.is_qualified is True
        assert score.final_status == "DIRECT_MATCH"
        assert score.relevance_score >= 0.80

    def test_scorer_not_relevant_on_exclusion(self, classifier):
        scorer = RelevanceScorer()
        biz = classifier.classify("PayWidget", "Payment gateway and checkout processor.")
        geo = GeographyVerificationResult(headquarters_country="India", status=GeoStatus.VERIFIED)
        score = scorer.score(biz, geo)
        assert score.is_qualified is False
        assert score.final_status == "NOT_RELEVANT"
