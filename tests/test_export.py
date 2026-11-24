"""
tests/test_export.py
====================
Unit tests for final export deliverables:
- startups.csv
- funding_rounds.csv
- articles.csv
- startups_funding.xlsx (5 distinct sheets)
"""

from __future__ import annotations

from pathlib import Path
from datetime import date
import openpyxl
import pandas as pd
import pytest

from database.models import Company, FundingRound
from database.repository import DatabaseRepository
from export.exporter import DataExporter
from export.excel_formatter import create_excel_workbook


@pytest.fixture
def test_env(tmp_path):
    db_file = tmp_path / "test.sqlite"
    export_dir = tmp_path / "exports"
    export_dir.mkdir()
    db_url = f"sqlite:///{db_file}"

    repo = DatabaseRepository(db_url=db_url)

    # Seed sample company & round
    comp = repo.save_company(
        Company(
            canonical_name="WealthAI",
            normalized_name="wealthai",
            website="https://wealthai.io",
            website_domain="wealthai.io",
            headquarters_country="United States",
            headquarters_city="San Francisco",
            primary_category="Wealth Management",
            secondary_categories=["Portfolio Analytics"],
            relevance_status="DIRECT_MATCH",
            classification_confidence=0.95,
            description="AI private market analytics",
        )
    )

    repo.save_funding_round(
        FundingRound(
            company_id=comp.id,
            funding_stage="Series A",
            amount=12_500_000.0,
            currency="USD",
            original_amount_text="$12.5M",
            announcement_date=date(2025, 3, 15),
            lead_investor="Sequoia Capital",
            investors=["Sequoia Capital", "Accel Partners"],
        )
    )

    repo.save_article(
        url="https://techcrunch.com/wealthai-round",
        canonical_url="https://techcrunch.com/wealthai-round",
        title="WealthAI raises $12.5M Series A",
        source_name="TechCrunch",
    )

    return export_dir, db_url


class TestExporter:

    def test_export_all_creates_all_files(self, test_env):
        export_dir, db_url = test_env
        exporter = DataExporter(export_dir=export_dir, db_url=db_url)
        files = exporter.export_all()

        assert "startups_csv" in files
        assert "funding_rounds_csv" in files
        assert "articles_csv" in files
        assert "excel_workbook" in files

        for path in files.values():
            assert path.exists()
            assert path.stat().st_size > 0

    def test_startups_csv_content(self, test_env):
        export_dir, db_url = test_env
        exporter = DataExporter(export_dir=export_dir, db_url=db_url)
        files = exporter.export_all()

        df = pd.read_csv(files["startups_csv"])
        assert len(df) == 1
        assert df.iloc[0]["Company Name"] == "WealthAI"
        assert df.iloc[0]["Country"] == "United States"
        assert df.iloc[0]["Primary Category"] == "Wealth Management"

    def test_funding_rounds_csv_content(self, test_env):
        export_dir, db_url = test_env
        exporter = DataExporter(export_dir=export_dir, db_url=db_url)
        files = exporter.export_all()

        df = pd.read_csv(files["funding_rounds_csv"])
        assert len(df) == 1
        assert df.iloc[0]["Company Name"] == "WealthAI"
        assert df.iloc[0]["Funding Round"] == "Series A"
        assert float(df.iloc[0]["Funding Amount"]) == 12_500_000.0
        assert df.iloc[0]["Currency"] == "USD"
        assert df.iloc[0]["Lead Investor"] == "Sequoia Capital"

    def test_excel_workbook_sheets_and_formatting(self, test_env):
        export_dir, db_url = test_env
        exporter = DataExporter(export_dir=export_dir, db_url=db_url)
        files = exporter.export_all()

        wb = openpyxl.load_workbook(files["excel_workbook"])
        sheet_names = wb.sheetnames

        expected_sheets = [
            "Funding Announcements",
            "Companies",
            "Funding Rounds",
            "Source Articles",
            "Records Requiring Review",
        ]
        assert sheet_names == expected_sheets

        # Test main sheet has headers
        ws_main = wb["Funding Announcements"]
        assert ws_main.cell(row=1, column=1).value == "Company Name"
        assert ws_main.cell(row=2, column=1).value == "WealthAI"
