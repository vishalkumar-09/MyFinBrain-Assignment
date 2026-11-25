"""
export/exporter.py
==================
Generates required deliverables:
1. startups.csv
2. funding_rounds.csv
3. articles.csv
4. startups_funding.xlsx
5. startups_funding.sqlite (already persisted by repository)

Formats all fields required by Section 15 of the project requirements.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any, List, Optional
import pandas as pd

from config.settings import EXPORT_DIR, DATABASE_URL
from database.repository import DatabaseRepository
from export.excel_formatter import create_excel_workbook

logger = logging.getLogger(__name__)


class DataExporter:
    """
    Coordinates dataset exports across CSV, Excel, and SQLite.
    """

    def __init__(
        self,
        export_dir: Path = EXPORT_DIR,
        db_url: str = DATABASE_URL,
    ) -> None:
        self.export_dir = export_dir
        self.export_dir.mkdir(parents=True, exist_ok=True)
        self.repo = DatabaseRepository(db_url=db_url)

    def export_all(self, in_memory_records: Optional[list[dict[str, Any]]] = None) -> dict[str, Path]:
        """
        Generate all required deliverables:
        - startups.csv
        - funding_rounds.csv
        - articles.csv
        - startups_funding.xlsx
        """
        logger.info("Starting data export to %s...", self.export_dir)

        # 1. Fetch data from SQLite repository or in-memory records
        companies = self.repo.get_all_companies()
        output_files: dict[str, Path] = {}

        # Prepare records
        comp_data = []
        round_data = []
        main_data = []
        review_data = []

        for comp in companies:
            sec_cats = ", ".join(comp.secondary_categories) if comp.secondary_categories else ""
            rounds = self.repo.get_funding_rounds_for_company(comp.id)

            is_qualified = (
                comp.relevance_status in ("DIRECT_MATCH", "ADJACENT_MATCH")
                and comp.headquarters_country in ("United States", "India")
            )
            is_review = comp.relevance_status == "NEEDS_REVIEW"

            # Filter out non-relevant noise from export deliverables
            if comp.relevance_status == "NOT_RELEVANT" and not comp.headquarters_country:
                continue

            # Populate Companies sheet/CSV
            if is_qualified or is_review or comp.headquarters_country in ("United States", "India"):
                comp_dict = {
                    "Company Name": comp.canonical_name,
                    "Country": comp.headquarters_country or "",
                    "City": comp.headquarters_city or "",
                    "Website": comp.website or "",
                    "Primary Category": comp.primary_category or "",
                    "Secondary Categories": sec_cats,
                    "Relevance Status": comp.relevance_status,
                    "Confidence Score": comp.classification_confidence,
                    "Description": comp.description or "",
                }
                comp_data.append(comp_dict)

            # If company has no rounds but is flagged for review
            if not rounds and is_review:
                review_data.append({
                    "Company Name": comp.canonical_name,
                    "Country": comp.headquarters_country or "",
                    "City": comp.headquarters_city or "",
                    "Primary Category": comp.primary_category or "",
                    "Relevance Status": comp.relevance_status,
                    "Funding Amount": "",
                    "Funding Round": "",
                    "Review Reason": "Classification or location unverified; no funding round recorded",
                    "Source URL": comp.website or "",
                })

            for rnd in rounds:
                inv_str = ", ".join(rnd.investors) if rnd.investors else ""
                round_dict = {
                    "Company Name": comp.canonical_name,
                    "Funding Round": rnd.funding_stage,
                    "Funding Amount": rnd.amount or "",
                    "Currency": rnd.currency or "",
                    "Original Amount Text": rnd.original_amount_text or "",
                    "Announcement Date": str(rnd.announcement_date or ""),
                    "Lead Investor": rnd.lead_investor or "",
                    "Investors": inv_str,
                }

                # Trace provenance back to article through evidence
                source_name = ""
                source_url = ""
                pub_date = ""
                if rnd.evidence_records:
                    for ev in rnd.evidence_records:
                        if ev.article:
                            source_name = ev.article.source_name
                            candidate_url = ev.article.canonical_url or ""
                            # Only accept URLs that look like real article pages,
                            # not search/query placeholder URLs.
                            _search_patterns = ("?s=", "?searchType=", "search?q=", "/search?", "?q=", "?query=")
                            if candidate_url and not any(p in candidate_url for p in _search_patterns):
                                source_url = candidate_url
                            if ev.article.published_at:
                                pub_date = str(ev.article.published_at.date())
                            break

                if not source_url and comp.website:
                    source_url = comp.website
                    source_name = "Company Website"

                # Include in Funding Rounds sheet/CSV if qualified or review
                if is_qualified or is_review:
                    round_data.append(round_dict)

                # Primary Funding Announcements sheet strictly for qualified US & India announcements
                if is_qualified:
                    eff_ann_date = str(rnd.announcement_date or pub_date or "")
                    main_dict = {
                        "Company Name": comp.canonical_name,
                        "Country": comp.headquarters_country or "",
                        "City": comp.headquarters_city or "",
                        "Website": comp.website or "",
                        "Company Description": comp.description or "",
                        "Primary Category": comp.primary_category or "",
                        "Secondary Categories": sec_cats,
                        "Relevance Status": comp.relevance_status,
                        "Funding Amount": rnd.amount or "",
                        "Currency": rnd.currency or "",
                        "Funding Round": rnd.funding_stage,
                        "Funding Announcement Date": eff_ann_date,
                        "Article Publication Date": pub_date,
                        "Lead Investor": rnd.lead_investor or "",
                        "Investors": inv_str,
                        "Source Name": source_name,
                        "Source URL": source_url,
                        "Verification Status": comp.relevance_status,
                    }
                    main_data.append(main_dict)

                if is_review or comp.relevance_status == "NEEDS_REVIEW":
                    review_data.append({
                        "Company Name": comp.canonical_name,
                        "Country": comp.headquarters_country or "",
                        "City": comp.headquarters_city or "",
                        "Primary Category": comp.primary_category or "",
                        "Relevance Status": comp.relevance_status,
                        "Funding Amount": rnd.amount or "",
                        "Funding Round": rnd.funding_stage,
                        "Review Reason": "Ambiguous location or business category",
                        "Source URL": source_url,
                    })

        # Sort deliverables newest-first for analyst readability
        main_data.sort(key=lambda r: r.get("Funding Announcement Date", ""), reverse=True)
        round_data.sort(key=lambda r: r.get("Announcement Date", ""), reverse=True)

        # Fetch articles from database
        art_data = []
        with self.repo.get_session() as session:
            from database.models import Article as DBArticle
            from sqlalchemy import select
            articles = session.execute(select(DBArticle)).scalars().all()
            for art in articles:
                art_data.append({
                    "Article Title": art.title,
                    "Source Name": art.source_name,
                    "Source URL": art.canonical_url,
                    "Published Date": str(art.published_at.date() if art.published_at else ""),
                    "Extraction Status": art.extraction_status,
                })
        art_data.sort(key=lambda r: r.get("Published Date", ""), reverse=True)

        # 2. Export startups.csv
        startups_csv = self.export_dir / "startups.csv"
        pd.DataFrame(comp_data).to_csv(startups_csv, index=False)
        output_files["startups_csv"] = startups_csv

        # 3. Export funding_rounds.csv
        rounds_csv = self.export_dir / "funding_rounds.csv"
        pd.DataFrame(round_data).to_csv(rounds_csv, index=False)
        output_files["funding_rounds_csv"] = rounds_csv

        # 4. Export articles.csv
        articles_csv = self.export_dir / "articles.csv"
        pd.DataFrame(art_data).to_csv(articles_csv, index=False)
        output_files["articles_csv"] = articles_csv

        # 5. Export startups_funding.xlsx
        excel_path = self.export_dir / "startups_funding.xlsx"
        create_excel_workbook(
            main_rows=main_data,
            company_rows=comp_data,
            round_rows=round_data,
            article_rows=art_data,
            review_rows=review_data,
            output_path=excel_path,
        )
        output_files["excel_workbook"] = excel_path

        logger.info("All files exported successfully to %s", self.export_dir)
        return output_files
