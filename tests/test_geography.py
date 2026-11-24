"""
tests/test_geography.py
=======================
Unit tests for geography verification (US & India target scope).

Rules tested:
- Headquarters in US verified (San Francisco, New York, Austin, etc.)
- Headquarters in India verified (Bengaluru, Mumbai, Delhi, etc.)
- Inconclusive location marked NEEDS_REVIEW (never assumed)
- Out-of-scope location (UK, Germany, Singapore) marked OUT_OF_SCOPE
- Does NOT infer headquarters from article publisher or investor location
- Cross-border operations (US HQ operating in India / India HQ operating in US)
"""

from __future__ import annotations

import pytest
from classification.geography_classifier import GeographyClassifier, GeoStatus


@pytest.fixture
def geo_classifier():
    return GeographyClassifier()


class TestGeographyVerification:

    def test_us_metro_san_francisco(self, geo_classifier):
        text = "San Francisco-based WealthAI announced today that it raised a Series A."
        res = geo_classifier.verify("WealthAI", article_text=text)
        assert res.status == GeoStatus.VERIFIED
        assert res.headquarters_country == "United States"
        assert res.headquarters_city == "San Francisco"
        assert res.confidence >= 0.80

    def test_us_metro_new_york(self, geo_classifier):
        text = "PortfolioOS, headquartered in New York, has secured seed funding."
        res = geo_classifier.verify("PortfolioOS", article_text=text)
        assert res.status == GeoStatus.VERIFIED
        assert res.headquarters_country == "United States"
        assert res.headquarters_city == "New York"

    def test_india_metro_bengaluru(self, geo_classifier):
        text = "Bengaluru-based AltAssets raised INR 30 Cr from family offices."
        res = geo_classifier.verify("AltAssets", article_text=text)
        assert res.status == GeoStatus.VERIFIED
        assert res.headquarters_country == "India"
        assert res.headquarters_city == "Bengaluru"

    def test_india_metro_mumbai(self, geo_classifier):
        text = "Mumbai-based WealthBridge secured fresh growth investment."
        res = geo_classifier.verify("WealthBridge", article_text=text)
        assert res.status == GeoStatus.VERIFIED
        assert res.headquarters_country == "India"
        assert res.headquarters_city == "Mumbai"

    def test_out_of_scope_country_marked(self, geo_classifier):
        text = "London-based AssetManager has raised 10 million pounds."
        res = geo_classifier.verify("AssetManager", article_text=text)
        assert res.status == GeoStatus.OUT_OF_SCOPE
        assert res.headquarters_country == "United Kingdom"

    def test_inconclusive_location_needs_review(self, geo_classifier):
        """When no reliable headquarters evidence is found, mark NEEDS_REVIEW."""
        text = "The stealth investment platform announced a $5M funding round led by top angels."
        res = geo_classifier.verify("StealthCo", article_text=text)
        assert res.status == GeoStatus.NEEDS_REVIEW
        assert res.confidence < 0.50

    def test_investor_location_not_inferred_as_hq(self, geo_classifier):
        """A US investor investing in an Indian startup must not change the company's HQ to US."""
        text = "Bengaluru-based FinStart has secured $10M from Silicon Valley-based Sequoia Capital."
        res = geo_classifier.verify("FinStart", article_text=text)
        assert res.status == GeoStatus.VERIFIED
        assert res.headquarters_country == "India"
        assert res.headquarters_city == "Bengaluru"

    def test_cross_border_operations(self, geo_classifier):
        """A US company operating in India should record India under operating_countries."""
        text = "San Francisco-based WealthAI announced expansion into India with new operations in Bengaluru."
        res = geo_classifier.verify("WealthAI", article_text=text)
        assert res.headquarters_country == "United States"
        assert "India" in res.operating_countries
