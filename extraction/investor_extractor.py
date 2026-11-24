"""
extraction/investor_extractor.py
================================
Extracts lead investors and participating investors from article text.

Handles patterns:
- Lead investor:
  - "led by <Investor>"
  - "co-led by <Investor 1> and <Investor 2>"
  - "<Investor> led the Series A round"
  - "under the leadership of <Investor>"
- Participating investors:
  - "with participation from <Inv1>, <Inv2>, and <Inv3>"
  - "joined by <Inv1> and <Inv2>"
  - "existing investors including <Inv1> also participated"
"""

from __future__ import annotations

import re
from typing import Optional
from pydantic import BaseModel


class ExtractedInvestors(BaseModel):
    lead_investor: Optional[str] = None
    investors: list[str] = []
    evidence: str = ""


# Lead investor regex patterns
_LEAD_PATTERNS = [
    re.compile(
        r"\b(?:led|co-led)\s+by\s+(?P<leads>[A-Z0-9][A-Za-z0-9\s&,\.]{2,80}?)(?:\s+with\s+participation|\s+and\s+joined|\.|\,)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<leads>[A-Z0-9][A-Za-z0-9\s&,\.]{2,50}?)\s+led\s+the\s+(?:funding|seed|round|Series\s+[A-Za-z])",
        re.IGNORECASE,
    ),
]

# Participating investors patterns
_PARTICIPATING_PATTERNS = [
    re.compile(
        r"\b(?:with\s+participation\s+from|joined\s+by|participating\s+investors\s+included?|backed\s+by)\s+(?P<others>[A-Z0-9][A-Za-z0-9\s&,\.]{2,120}?)(?:\.|\n|as\s+well\s+as)",
        re.IGNORECASE,
    ),
]

# Noise tokens to strip
_CLEAN_INVESTOR_RE = re.compile(
    r"\b(?:venture\s+capital|capital|partners|ventures|fund|management|group|investments|holdings)\b",
    re.IGNORECASE,
)


def _clean_investor_name(name: str) -> str:
    """Clean individual investor name."""
    clean = re.sub(r"^(?:and|from|with|by)\s+", "", name.strip(), flags=re.IGNORECASE)
    clean = clean.strip(" ,.;:-")
    return clean


def parse_investor_list(text_block: str) -> list[str]:
    """Split comma- and 'and'-separated list of investor names."""
    if not text_block:
        return []

    # Replace ' and ' with comma
    standardized = re.sub(r"\s+and\s+", ", ", text_block)
    tokens = [t.strip() for t in standardized.split(",") if t.strip()]

    results = []
    for tok in tokens:
        cleaned = _clean_investor_name(tok)
        if len(cleaned) >= 2 and cleaned.lower() not in ("others", "existing investors", "angel investors", "prominent angels"):
            results.append(cleaned)
    return results


def extract_investors(article_text: str) -> ExtractedInvestors:
    """
    Extract lead investor and list of participating investors with evidence.
    """
    if not article_text:
        return ExtractedInvestors()

    lead_investor = None
    other_investors: list[str] = []
    evidence_parts: list[str] = []

    # 1. Lead investor
    for pat in _LEAD_PATTERNS:
        match = pat.search(article_text)
        if match:
            raw_leads = match.group("leads")
            leads = parse_investor_list(raw_leads)
            if leads:
                lead_investor = leads[0]
                if len(leads) > 1:
                    other_investors.extend(leads[1:])
                evidence_parts.append(match.group(0).strip())
                break

    # 2. Participating investors
    for pat in _PARTICIPATING_PATTERNS:
        match = pat.search(article_text)
        if match:
            raw_others = match.group("others")
            others = parse_investor_list(raw_others)
            for inv in others:
                if inv != lead_investor and inv not in other_investors:
                    other_investors.append(inv)
            evidence_parts.append(match.group(0).strip())
            break

    # Deduplicate and sort
    seen = set()
    cleaned_investors = []
    if lead_investor:
        cleaned_investors.append(lead_investor)
        seen.add(lead_investor.lower())

    for inv in other_investors:
        if inv.lower() not in seen:
            seen.add(inv.lower())
            cleaned_investors.append(inv)

    return ExtractedInvestors(
        lead_investor=lead_investor,
        investors=cleaned_investors,
        evidence="; ".join(evidence_parts),
    )
