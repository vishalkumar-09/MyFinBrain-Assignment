"""
extraction/funding_extractor.py
===============================
Orchestrates full funding round information extraction from articles.

Integrates:
- Amount parser (USD, INR, EUR, GBP, undisclosed, numeric normalization)
- Company extractor (company name, city, country, description, website)
- Investor extractor (lead investor, participating investors list)
- Date extractor (distinguishes announcement date from publication date)
- Funding stage extractor (Pre-seed, Seed, Angel, Series A-D+, Growth, Debt, Strategic)
- Evidence tracking for all extracted fields

Rules enforced:
1. Distinguishes a startup receiving funding from a VC raising a new fund.
2. Preserves evidence for every critical field.
3. Unknown values remain None.
4. Does not infer funding amounts from unrelated valuations or revenue numbers.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional
from pydantic import BaseModel, Field

from config.keywords import FUNDING_STAGE_MAP
from sources.base import Article
from extraction.amount_parser import extract_funding_amount, ParsedAmount
from extraction.company_extractor import extract_company_info, ExtractedCompany
from extraction.investor_extractor import extract_investors, ExtractedInvestors
from extraction.date_extractor import resolve_dates


class ExtractedFundingRound(BaseModel):
    """Complete structured extraction of a startup funding announcement."""
    # Company details
    company_name: str
    company_website: Optional[str] = None
    company_description: Optional[str] = None
    headquarters_country: Optional[str] = None
    headquarters_city: Optional[str] = None

    # Funding round details
    funding_stage: str = "Other"
    funding_amount: Optional[float] = None
    currency: Optional[str] = None
    original_amount_text: Optional[str] = None
    is_undisclosed: bool = False

    # Dates
    announcement_date: Optional[date] = None
    article_publication_date: Optional[date] = None

    # Investors
    lead_investor: Optional[str] = None
    investors: list[str] = Field(default_factory=list)

    # Provenance & evidence
    source_url: str
    source_name: str
    article_title: str
    supporting_evidence: dict[str, str] = Field(default_factory=dict)

    # Negative flags
    is_vc_fund_raise: bool = False


# Stage extraction regex
_STAGE_REGEX = re.compile(
    r"\b(?P<stage>Pre-Seed|Pre\s+Seed|Angel(?:\s+Round|\s+Investment)?|Seed(?:\s+Round|\s+Stage|\s+Funding)?|Series\s+[A-F](?:-\d+)?|Growth(?:\s+Round|\s+Equity)?|Venture\s+Debt|Debt\s+Financing|Strategic(?:\s+Round|\s+Investment)?|Bridge(?:\s+Round|\s+Financing)?)\b",
    re.IGNORECASE,
)


def extract_funding_stage(text: str) -> tuple[str, str]:
    """
    Identify funding stage from text and map to canonical name.
    Returns (canonical_stage, evidence).
    """
    if not text:
        return "Other", ""

    match = _STAGE_REGEX.search(text)
    if match:
        raw_stage = match.group("stage").strip().lower()
        # Clean hyphen or double space
        clean_key = re.sub(r"\s+", " ", raw_stage)
        canonical = FUNDING_STAGE_MAP.get(clean_key, "Other")
        if canonical == "Other":
            # Direct Series match fallback
            if "series a" in clean_key:
                canonical = "Series A"
            elif "series b" in clean_key:
                canonical = "Series B"
            elif "series c" in clean_key:
                canonical = "Series C"
            elif "series d" in clean_key:
                canonical = "Series D"
            elif "seed" in clean_key:
                canonical = "Seed"
            elif "angel" in clean_key:
                canonical = "Angel"
        return canonical, match.group(0)

    # Undisclosed round check
    if re.search(r"\bundisclosed\s+(?:round|funding)\b", text, re.IGNORECASE):
        return "Undisclosed", "undisclosed funding"

    return "Other", ""


class FundingExtractor:
    """
    Extraction pipeline orchestrator.
    Processes an Article into an ExtractedFundingRound.
    """

    def extract(self, article: Article) -> Optional[ExtractedFundingRound]:
        """
        Extract structured funding data from an Article.
        Returns None if no valid company or funding announcement is detected.
        """
        title = article.title or ""
        body = article.full_text or article.summary or ""
        combined_text = f"{title}\n\n{body}"

        # 1. Company extraction
        company_info: Optional[ExtractedCompany] = extract_company_info(title=title, text=body)
        if not company_info or not company_info.name:
            return None

        # 2. Funding amount extraction
        amount_info: Optional[ParsedAmount] = extract_funding_amount(combined_text)

        # Check if this is a VC firm fund-raise rather than startup round
        is_vc_fund = False
        if amount_info and amount_info.is_vc_fund_raise:
            is_vc_fund = True

        # 3. Funding stage extraction
        stage, stage_evidence = extract_funding_stage(combined_text[:1500])

        # 4. Investor extraction
        investor_info: ExtractedInvestors = extract_investors(combined_text)

        # 5. Date extraction
        dates = resolve_dates(published_at=article.published_at, article_text=body)

        # Assemble evidence dictionary
        evidence: dict[str, str] = {}
        if company_info.evidence:
            evidence["company_name"] = company_info.evidence
        if amount_info and amount_info.evidence:
            evidence["funding_amount"] = amount_info.evidence
        if stage_evidence:
            evidence["funding_stage"] = stage_evidence
        if investor_info.evidence:
            evidence["investors"] = investor_info.evidence
        if dates.announcement_date_evidence:
            evidence["announcement_date"] = dates.announcement_date_evidence

        return ExtractedFundingRound(
            company_name=company_info.name,
            company_website=company_info.website,
            company_description=company_info.description,
            headquarters_country=company_info.headquarters_country,
            headquarters_city=company_info.headquarters_city,
            funding_stage=stage,
            funding_amount=amount_info.amount if amount_info else None,
            currency=amount_info.currency if amount_info else None,
            original_amount_text=amount_info.raw_text if amount_info else None,
            is_undisclosed=amount_info.is_undisclosed if amount_info else False,
            announcement_date=dates.announcement_date,
            article_publication_date=dates.publication_date,
            lead_investor=investor_info.lead_investor,
            investors=investor_info.investors,
            source_url=article.canonical_url or article.url,
            source_name=article.source_name,
            article_title=title,
            supporting_evidence=evidence,
            is_vc_fund_raise=is_vc_fund,
        )
