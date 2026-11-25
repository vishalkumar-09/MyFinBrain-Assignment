"""
classification/business_classifier.py
=====================================
Multi-category company classification engine.

Target Categories:
1. Private Markets
   (Private equity, private credit/debt, private market infrastructure, pre-IPO platforms,
    secondary markets, unlisted shares, private market portfolio management/analytics)
2. Alternative Investments
   (Alternative asset management, fractional ownership, real estate investment platforms,
    alternative marketplaces, hedge fund tech, commodities, collectibles, infrastructure)
3. Wealth Management
   (Digital wealth management, wealthtech, investment advisory, portfolio management,
    family office tech, asset management tech, financial planning, digital brokerage)
4. Adjacent Infrastructure
   (Investment infrastructure, portfolio analytics, family office software, private market data,
    asset allocation technology, investment research platforms, financial advisory infrastructure)

Strict Negative Exclusions:
- Payment-only businesses (payment gateways, merchant processing, POS, UPI apps)
- Lending-only businesses (BNPL, payday loans, personal loan apps, microfinance)
- Insurance-only businesses (insurtech, policy brokers, claims software)
- General e-commerce and generic non-investment software

Allowed Statuses:
- DIRECT_MATCH
- ADJACENT_MATCH
- NOT_RELEVANT
- NEEDS_REVIEW
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class RelevanceStatus(str, Enum):
    DIRECT_MATCH = "DIRECT_MATCH"
    ADJACENT_MATCH = "ADJACENT_MATCH"
    NOT_RELEVANT = "NOT_RELEVANT"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ClassificationResult(BaseModel):
    primary_category: Optional[str] = None
    secondary_categories: list[str] = Field(default_factory=list)
    relevance_status: RelevanceStatus = RelevanceStatus.NOT_RELEVANT
    relevance_score: float = 0.0  # 0.0 to 1.0
    classification_confidence: float = 0.0  # 0.0 to 1.0
    classification_reasoning: str = ""
    supporting_evidence: list[str] = Field(default_factory=list)


# Category Keyword Mappings
_CATEGORIES = {
    "Private Markets": [
        "private equity", "private credit", "private debt", "private market", "private markets",
        "pre-ipo shares", "pre-ipo platform", "pre-ipo marketplace", "pre-ipo investing",
        "secondary market", "unlisted share", "unlisted stock",
        "private investment platform", "private market portfolio", "private asset", "private assets",
        "venture secondary", "private capital", "tokenized capital markets", "tokenised capital markets",
        "tokenised markets", "tokenized markets",
    ],
    "Alternative Investments": [
        "alternative investment", "alternative asset", "alternative assets", "alternatives infrastructure",
        "fractional ownership", "real estate investment platform", "real estate investing",
        "fractional real estate", "hedge fund technology", "hedge funds",
        "commodities investment", "collectibles investment", "art investment",
        "infrastructure investment", "crypto asset management", "wine investment",
        "fixed-income", "fixed income", "corporate bonds", "tokenized housing", "tokenised housing",
        "tokenized real estate", "tokenised assets", "tokenized assets",
        "tokenised investment funds", "tokenized investment funds",
        "tokenised funds", "tokenized funds",
        "private funds", "compute risk markets", "land markets", "asset-backed",
    ],
    "Wealth Management": [
        "wealth management", "wealthtech", "wealth tech", "wealth-tech", "digital wealth",
        "investment advisory", "financial advisory", "wealth advisory", "portfolio management",
        "family office technology", "family office software", "for family offices", "family office platform",
        "asset management technology",
        "asset management platform", "wealth firm", "wealth firms", "wealth advisor", "wealth advisors",
        "financial advisor", "financial advisors", "financial advisers", "advisor succession",
        "financial planning platform", "investment management platform", "digital brokerage",
        "robo-advisor", "robo advisory", "personalized investment", "registered investment advisor",
        "ria", "private banking", "stock trading platform", "us stock trading", "trading platform",
        "mutual fund", "brokerage startup", "will and estate", "estate planning", "succession planning",
        "wealth creators", "personalized financial advice", "personalised financial advice",
        "portfolio tech", "portfolio technology", "invest with ai",
    ],
    "Adjacent Infrastructure": [
        "investment infrastructure", "portfolio analytics", "family office software",
        "private market data", "asset allocation", "investment research", "credit research",
        "corporate credit data", "financial advisory infrastructure", "fund administration software",
        "capital table management", "cap table", "capital markets infrastructure",
        "investment management", "investment risk", "risk models", "investment banking",
        "market predictions into stock portfolios", "due diligence calls", "institutional investors",
        "institutional capital", "proxy voting", "corporate access", "buy-side", "fintech infrastructure",
        "equity research", "wealth distribution",
    ],
}

# Strict Exclusions (Negative Patterns)
_NEGATIVE_PATTERNS = {
    "Payment-only": re.compile(
        r"\b(?:payment\s+gateway|merchant\s+acquir(?:ing|er)|pos\s+terminal|payment\s+processing|"
        r"payments?\s+infrastructure|cross-border\s+payments?|checkout\s+solution|bill\s+payment|"
        r"money\s+transfer|remittance|p2p\s+payments?)\b",
        re.IGNORECASE,
    ),
    "Lending-only": re.compile(
        r"\b(?:payday\s+loans?|personal\s+loan\s+app|buy\s+now\s+pay\s+later|bnpl|instant\s+credit|"
        r"micro-lending|microlending|credit\s+card\s+issuance|predatory\s+lending|"
        r"home\s+financing|mortgage\s+platform|consumer\s+lending|loan\s+servicer|"
        r"manufactured\s+housing\s+finance|housing\s+finance|preferential\s+issue|digital\s+lending|"
        r"small\s+finance\s+bank|\bsfb\b|nbfc)\b",
        re.IGNORECASE,
    ),
    "Insurance-only": re.compile(
        r"\b(?:insurtech|insurance\s+broker|health\s+insurance|auto\s+insurance|life\s+insurance|"
        r"insurance\s+claims|policy\s+comparison|insurance\s+underwriting|insurance\s+and\s+mobility|"
        r"managing\s+general\s+agent|excess\s*(?:&|and)\s*surplus|"
        r"for\s+lenders\s+and\s+insurers|across\s+insurance)\b",
        re.IGNORECASE,
    ),
    "General E-commerce": re.compile(
        r"\b(?:online\s+marketplace\s+for\s+goods|e-commerce\s+store|d2c\s+(?:brand|lifestyle|startup)|retail\s+shopping|"
        r"grocery\s+delivery|quick\s+commerce|instant\s+delivery|luxury\s+watch|watch\s+brand)\b",
        re.IGNORECASE,
    ),
    "Generic Software": re.compile(
        r"\b(?:hr\s+management\s+software|payroll\s+only|applicant\s+tracking|crm\s+for\s+sales|"
        r"marketing\s+automation|sales\s+automation|crm\s+space|accounting\s+practices|"
        r"accounting\s+software|video\s+production\s+(?:startup|platform)|multi-agent\s+video|"
        r"apartment\s+touring|vendor\s+recovery|firmware|software\s+supply\s+chain|"
        r"cybersecurity|product\s+security|compliance\s+management\s+software)\b",
        re.IGNORECASE,
    ),
    "Non-Investment Sector": re.compile(
        r"\b(?:spacetech|space-tech|plastic\s+recycling|circular\s+economy|chip\s+startup|"
        r"semiconductor|defence\s+manufacturing|defense\s+manufacturing|healthcare\s+administration|"
        r"dental\s+membership|dentistry|dental\s+(?:care|cleanings|practices)|cardiac|remote\s+monitoring|medtech|"
        r"hospitality\s+brand|hotel\s+(?:brand|portfolio|chain)|study\s+abroad|edtech|"
        r"subscription-based\s+air\s+conditioning|air\s+conditioning|climatetech|"
        r"cold[\s-]chain|logistics\s+provider|"
        r"compulsorily\s+convertible\s+preference\s+shares|non-banking\s+financ(?:e|ial)|"
        r"electric\s+bus|electric\s+vehicle|robotaxis?|neocloud|"
        r"farm\s+equipment|agricultural\s+equipment|lists?\s+on\s+bse)\b",
        re.IGNORECASE,
    ),
    "Fundraise / PE Buyout": re.compile(
        r"\b(?:real\s+estate\s+debt\s+fund|ai-driven\s+hedge\s+fund|fund\s+launch|"
        r"debt\s+vintage|infrastructure\s+debt|co-investment\s+vehicles|final\s+close\s+of\s+its|"
        r"entered\s+into\s+a\s+definitive\s+agreement\s+for\s+funds)\b",
        re.IGNORECASE,
    ),
}


class BusinessClassifier:
    """
    Evaluates startup products, services, and descriptions against target investment categories.
    """

    def classify(
        self,
        company_name: str,
        description: Optional[str] = None,
        article_text: Optional[str] = None,
    ) -> ClassificationResult:
        """
        Classify a company based on its description, business model, and contextual evidence.
        """
        identity_text = f"{company_name}\n{description or ''}".lower()
        combined = f"{identity_text}\n{article_text or ''}".lower()

        # 1. Check strict exclusions (hard categories cannot be bypassed by investor-bio noise)
        _INVESTMENT_IDENTITY_TERMS = (
            "wealth management", "wealthtech", "private equity",
            "alternative investment", "private markets",
        )
        _HARD_EXCLUSIONS = {"Insurance-only", "Non-Investment Sector", "Generic Software", "General E-commerce", "Fundraise / PE Buyout"}
        for exc_name, pat in _NEGATIVE_PATTERNS.items():
            match = pat.search(combined)
            if match:
                allow_exemption = (
                    exc_name not in _HARD_EXCLUSIONS
                    and any(k in identity_text for k in _INVESTMENT_IDENTITY_TERMS)
                )
                if not allow_exemption:
                    return ClassificationResult(
                        primary_category="Unrelated Fintech / Non-Investment",
                        relevance_status=RelevanceStatus.NOT_RELEVANT,
                        relevance_score=0.1,
                        classification_confidence=0.9,
                        classification_reasoning=f"Excluded as {exc_name} business without relevant investment focus.",
                        supporting_evidence=[match.group(0)],
                    )

        # 2. Check category matches
        category_hits: dict[str, list[str]] = {}
        for category, keywords in _CATEGORIES.items():
            hits = [kw for kw in keywords if re.search(rf"\b{re.escape(kw)}\b", combined)]
            if hits:
                category_hits[category] = hits

        if not category_hits:
            # Check if general investment context exists
            if any(term in combined for term in ["investing", "investors", "assets", "securities"]):
                return ClassificationResult(
                    primary_category=None,
                    relevance_status=RelevanceStatus.NEEDS_REVIEW,
                    relevance_score=0.4,
                    classification_confidence=0.5,
                    classification_reasoning="Mention of investments but lacks specific private markets/wealthtech keyword match.",
                    supporting_evidence=[],
                )
            return ClassificationResult(
                primary_category=None,
                relevance_status=RelevanceStatus.NOT_RELEVANT,
                relevance_score=0.0,
                classification_confidence=0.85,
                classification_reasoning="No match with target private markets, wealthtech, or alternative assets categories.",
                supporting_evidence=[],
            )

        # 3. Determine primary & secondary categories
        # Rank categories by hit count and keyword specificity
        ranked = sorted(category_hits.items(), key=lambda kv: len(kv[1]), reverse=True)
        primary = ranked[0][0]
        secondaries = [cat for cat, _ in ranked[1:]]

        # Gather evidence snippets
        all_hits = [hit for _, hits in category_hits.items() for hit in hits]

        # Determine status: DIRECT_MATCH vs ADJACENT_MATCH
        if primary in ("Private Markets", "Alternative Investments", "Wealth Management"):
            status = RelevanceStatus.DIRECT_MATCH
            score = 0.95 if len(all_hits) >= 2 else 0.85
        else:
            status = RelevanceStatus.ADJACENT_MATCH
            score = 0.75

        confidence = min(0.95, 0.70 + (0.05 * len(all_hits)))
        reasoning = f"Direct alignment with {primary} based on product matches: {', '.join(all_hits[:4])}."

        return ClassificationResult(
            primary_category=primary,
            secondary_categories=secondaries,
            relevance_status=status,
            relevance_score=score,
            classification_confidence=confidence,
            classification_reasoning=reasoning,
            supporting_evidence=all_hits[:5],
        )
