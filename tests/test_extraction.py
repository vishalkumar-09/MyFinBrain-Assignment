"""
tests/test_extraction.py
========================
Unit tests for article parsing, company extraction, investor extraction,
date extraction, and full funding round orchestration.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import pytest

from sources.base import Article, ExtractionStatus
from extraction.article_parser import ArticleParser
from extraction.company_extractor import extract_company_info, extract_company_from_title, extract_location
from extraction.investor_extractor import extract_investors
from extraction.date_extractor import resolve_dates, extract_announcement_date
from extraction.funding_extractor import FundingExtractor, extract_funding_stage


SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>WealthAI raises $12.5M Series A for private market analytics</title>
  <meta property="og:title" content="WealthAI raises $12.5M Series A for private market analytics">
  <meta name="author" content="Sarah Chen">
  <meta property="article:published_time" content="2025-03-15T10:00:00Z">
</head>
<body>
  <article>
    <h1>WealthAI raises $12.5M Series A for private market analytics</h1>
    <p>San Francisco-based WealthAI, an AI-powered private market analytics platform for family offices, announced on March 15, 2025 that it has raised $12.5 million in a Series A funding round.</p>
    <p>The financing was led by Sequoia Capital, with participation from Accel Partners, Founders Fund, and Bessemer Venture Partners.</p>
    <p>The company operates at wealthai.io and plans to use the proceeds to expand its portfolio management solutions.</p>
  </article>
</body>
</html>
"""

INDIAN_DEAL_HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>WealthBridge bags INR 50 Cr Series B to expand alternative investment platform</title>
</head>
<body>
  <main>
    <p>Bengaluru-based WealthBridge, which develops alternative investment infrastructure, has raised INR 50 Cr in Series B funding.</p>
    <p>The round was led by Tiger Global with participation from Peak XV and Elevation Capital.</p>
  </main>
</body>
</html>
"""

NON_FUNDING_HTML = """
<!DOCTYPE html>
<html>
<head><title>Top 10 Trends in WealthTech for 2025</title></head>
<body>
  <article>
    <p>Wealth management technology is changing rapidly. Here are the top ten trends shaping private markets and portfolio analytics this year.</p>
  </article>
</body>
</html>
"""


class TestArticleParser:

    def test_parse_sample_html(self):
        parser = ArticleParser()
        article = parser.parse_html(SAMPLE_HTML, url="https://example.com/wealthai-round")
        assert article.extraction_status == ExtractionStatus.SUCCESS
        assert article.full_text is not None
        assert "WealthAI" in article.full_text
        assert article.title == "WealthAI raises $12.5M Series A for private market analytics"
        assert article.author == "Sarah Chen"
        assert article.published_at is not None
        assert article.content_hash is not None

    def test_parse_empty_html_handles_gracefully(self):
        parser = ArticleParser()
        article = parser.parse_html("", url="https://example.com/empty")
        assert article.extraction_status == ExtractionStatus.FAILED
        assert article.full_text is None


class TestCompanyExtractor:

    def test_extract_company_from_headline(self):
        title = "WealthAI raises $12.5M Series A to expand platform"
        res = extract_company_from_title(title)
        assert res is not None
        name, _ = res
        assert name == "WealthAI"

    def test_extract_location_us(self):
        text = "San Francisco-based WealthAI announced fresh funding."
        city, country = extract_location(text)
        assert city == "San Francisco"
        assert country == "United States"

    def test_extract_location_india(self):
        text = "Bengaluru-based WealthBridge secured seed capital."
        city, country = extract_location(text)
        assert city == "Bengaluru"
        assert country == "India"

    def test_extract_company_full_info(self):
        title = "WealthAI raises $12.5M Series A"
        body = "San Francisco-based WealthAI, an AI-powered private market analytics platform, has raised funding. Visit wealthai.io for details."
        comp = extract_company_info(title, body)
        assert comp is not None
        assert comp.name == "WealthAI"
        assert comp.headquarters_city == "San Francisco"
        assert comp.headquarters_country == "United States"
        assert comp.website == "https://wealthai.io"


class TestInvestorExtractor:

    def test_extract_lead_and_participating_investors(self):
        text = "The round was led by Sequoia Capital, with participation from Accel Partners, Founders Fund, and Bessemer Venture Partners."
        invs = extract_investors(text)
        assert invs.lead_investor == "Sequoia Capital"
        assert "Accel Partners" in invs.investors
        assert "Founders Fund" in invs.investors
        assert "Bessemer Venture Partners" in invs.investors

    def test_investor_name_cleanup(self):
        text = "Led by Tiger Global with participation from Peak XV."
        invs = extract_investors(text)
        assert invs.lead_investor == "Tiger Global"
        assert "Peak XV" in invs.investors


class TestDateExtractor:

    def test_extract_announcement_date(self):
        text = "The company announced on March 15, 2025 that it closed a seed round."
        ann_date, ev = extract_announcement_date(text)
        assert ann_date == date(2025, 3, 15)
        assert "March 15, 2025" in ev

    def test_resolve_dates(self):
        pub_dt = datetime(2025, 3, 15, 12, 0, tzinfo=timezone.utc)
        text = "Announced on March 14, 2025."
        dates = resolve_dates(published_at=pub_dt, article_text=text)
        assert dates.publication_date == date(2025, 3, 15)
        assert dates.announcement_date == date(2025, 3, 14)


class TestFundingStageExtractor:

    def test_series_a(self):
        stage, _ = extract_funding_stage("WealthAI raises $10M Series A round")
        assert stage == "Series A"

    def test_seed(self):
        stage, _ = extract_funding_stage("Startup secures $3M seed funding")
        assert stage == "Seed"

    def test_pre_seed(self):
        stage, _ = extract_funding_stage("Founder raises $500K Pre-Seed check")
        assert stage == "Pre-Seed"

    def test_venture_debt(self):
        stage, _ = extract_funding_stage("Fintech secures $20M venture debt facility")
        assert stage == "Venture Debt"


class TestFundingExtractorOrchestration:

    def test_orchestrate_us_deal(self):
        parser = ArticleParser()
        article = parser.parse_html(SAMPLE_HTML, url="https://techcrunch.com/wealthai-series-a")
        article.source_name = "TechCrunch"

        extractor = FundingExtractor()
        round_data = extractor.extract(article)

        assert round_data is not None
        assert round_data.company_name == "WealthAI"
        assert round_data.funding_amount == 12_500_000.0
        assert round_data.currency == "USD"
        assert round_data.funding_stage == "Series A"
        assert round_data.headquarters_country == "United States"
        assert round_data.headquarters_city == "San Francisco"
        assert round_data.lead_investor == "Sequoia Capital"
        assert "Accel Partners" in round_data.investors
        assert round_data.announcement_date == date(2025, 3, 15)
        assert round_data.company_website == "https://wealthai.io"
        assert not round_data.is_vc_fund_raise

    def test_orchestrate_indian_deal(self):
        parser = ArticleParser()
        article = parser.parse_html(INDIAN_DEAL_HTML, url="https://inc42.com/wealthbridge-series-b")
        article.source_name = "Inc42"

        extractor = FundingExtractor()
        round_data = extractor.extract(article)

        assert round_data is not None
        assert round_data.company_name == "WealthBridge"
        assert round_data.funding_amount == 500_000_000.0  # 50 Cr
        assert round_data.currency == "INR"
        assert round_data.funding_stage == "Series B"
        assert round_data.headquarters_country == "India"
        assert round_data.headquarters_city == "Bengaluru"
        assert round_data.lead_investor == "Tiger Global"

    def test_non_funding_article_returns_none(self):
        parser = ArticleParser()
        article = parser.parse_html(NON_FUNDING_HTML, url="https://example.com/trends")
        article.source_name = "Blog"

        extractor = FundingExtractor()
        round_data = extractor.extract(article)
        assert round_data is None
