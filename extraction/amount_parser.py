"""
extraction/amount_parser.py
===========================
Robust parser for startup funding amounts across global and Indian currency systems.

Supported patterns:
- USD: $10M, $12.5 million, USD 20 million, $1.2B, $500k, $750,000
- INR: ₹50 crore, INR 25 Cr, Rs. 10 crore, Rs 50 lakh, ₹100 Cr.
- EUR: €5 million, EUR 15M
- GBP: £8 million, GBP 12M
- Undisclosed: "undisclosed amount", "undisclosed sum", "undisclosed funding"

Important rules:
1. Preserve original representation string.
2. Normalize currencies into ISO 4217 (USD, INR, EUR, GBP).
3. Compute exact numeric value using units (million=1e6, crore=1e7, lakh=1e5, billion=1e9, k=1e3).
4. Never assume exchange rates between different currencies.
5. Distinguish funding raised by a startup from a VC raising a new fund
   (e.g., "raises $100M fund" -> VC fund, not startup round).
6. Discard valuation / revenue figures ("valued at $1B", "ARR of $10M").
"""

from __future__ import annotations

import re
from typing import Optional
from pydantic import BaseModel, Field

from config.keywords import AMOUNT_UNITS, CURRENCY_MAP


class ParsedAmount(BaseModel):
    """Structured representation of an extracted funding amount."""
    raw_text: str
    amount: Optional[float] = None
    currency: Optional[str] = None
    is_undisclosed: bool = False
    evidence: str = ""
    is_vc_fund_raise: bool = False  # e.g., VC raised a $100M fund


# Regex patterns
_CURRENCY_SYMBOLS = r"(?:\$|₹|€|£|¥|USD|INR|EUR|GBP|Rs\.?|Rupees?)"
_NUMBER_PART = r"(?:\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)"
_UNIT_PART = r"(?:million|mn|m|billion|bn|b|crore|crores|cr\.?|lakh|lakhs|thousand|k)"

# Pattern for standard funding amounts like "$12.5 million", "USD 20M", "₹50 crore", "Rs 25 Cr"
_AMOUNT_REGEX = re.compile(
    rf"(?P<prefix_curr>{_CURRENCY_SYMBOLS})\s*"
    rf"(?P<number>{_NUMBER_PART})\s*"
    rf"(?P<unit>{_UNIT_PART})?"
    rf"|"
    rf"(?P<number_alt>{_NUMBER_PART})\s*"
    rf"(?P<unit_alt>{_UNIT_PART})\s*"
    rf"(?P<suffix_curr>{_CURRENCY_SYMBOLS})",
    re.IGNORECASE,
)

# Undisclosed pattern
_UNDISCLOSED_REGEX = re.compile(
    r"\b(?:undisclosed\s+(?:amount|sum|funding|round|size)|funding\s+amount\s+was\s+not\s+disclosed)\b",
    re.IGNORECASE,
)

# Negative context: VC fund / Fund close / Hedge fund LP raise (distinguish from company funding)
_VC_FUND_CONTEXT = re.compile(
    r"\b(?:closes?|closed|launch(?:es|ed)?|raises?|raised|hits?|marks?|unveils?|unveiled|commits?|committed)\s+(?:its\s+|a\s+)?(?:[^\.]{0,55}?\s+)?(?:debut|inaugural|new|first|second|third|fourth|fifth|sixth|seventh|eighth|venture|growth|private\s+equity|private\s+credit|real\s+estate\s+debt|senior\s+infrastructure\s+debt|infrastructure\s+debt|debt|credit|investment|pre-ipo|deeptech|deep-tech|special\s+situations|consumer)\s+(?:fund|pool|vehicle|strategy|vintage)\b"
    r"|\b(?:first|final|second)\s+close\s+(?:of|for)\s+(?:its\s+|a\s+)?[^\.]{0,40}?\bfund\b"
    r"|\bFund\s+(?:I|II|III|IV|V|VI|VII|VIII|IX|X|\d+)\b\s+(?:closes?|at|with)"
    r"|\bcontinuation\s+(?:fund|vehicle)\b"
    r"|\bfund\s+(?:size\s+of|targeting|closed\s+at)\b"
    r"|\b(?:private\s+equity\s+pool|credit\s+strategy|credit\s+fund|venture\s+firm\s+raises|(?:ai-driven\s+|new\s+|newly\s+launched\s+)?hedge\s+fund\s+(?:raises?|closes?|launches?)|fund\s+launch)\b",
    re.IGNORECASE,
)

# Negative context: Valuation, revenue, AUM, or cumulative historical totals
_VALUATION_REVENUE_CONTEXT = re.compile(
    r"\b(?:valued\s+at|valuation\s+of|post-money\s+valuation|pre-money\s+valuation|"
    r"revenue\s+of|ARR\s+of|annual\s+revenue|in\s+(?:monthly|annual|yearly)?\s*revenue|"
    r"assets\s+under\s+(?:management|oversight|its\s+oversight)|AUM|"
    r"mark\s+in\s+(?:private\s+market\s+)?(?:assets|client\s+assets)|"
    r"in\s+(?:advised\s+|billable\s+|client\s+){0,2}assets\b|"
    r"assets\s+(?:held\s+on|on\s+its\s+platform|passed|exceed|stand\s+at)|"
    r"(?:grew\s+)?from\s+(?:rs\.?|₹|\$)\s*[\d,\.]+\s*(?:cr|crore|lakh|lakhs|million|bn)?\s+to)\b"
    r"|(?<![a-zA-Z])(?:billion|bn|million|mn|crore|cr)\s+(?:mark\s+)?in\s+(?:private\s+market\s+)?(?:assets|client\s+assets|assets\s+on|advised\s+(?:billable\s+)?assets)\b",
    re.IGNORECASE,
)
_PRECEDING_TOTAL_CONTEXT_RE = re.compile(
    r"\b(?:total\s+(?:capital|funding)\s+raised\s+(?:to|past)|cumulative\s+(?:funding|capital)\s+(?:to|past)|"
    r"(?:passes?|past)\s+(?:the\s+)?)$",
    re.IGNORECASE,
)
_IMMEDIATE_NON_ROUND_SUFFIX_RE = re.compile(
    r"^\s*(?:(?:pre-money|post-money)\s+)?valuation\b",
    re.IGNORECASE,
)


def normalize_currency(curr_str: str) -> Optional[str]:
    """Normalize raw currency symbol or code to standard ISO 4217."""
    clean = curr_str.strip().lower()
    return CURRENCY_MAP.get(clean)


def parse_numeric_amount(number_str: str, unit_str: Optional[str]) -> float:
    """Calculate absolute numerical float value from number string and unit."""
    cleaned_num = number_str.replace(",", "").strip()
    val = float(cleaned_num)
    if unit_str:
        clean_unit = unit_str.strip().lower().rstrip(".")
        multiplier = AMOUNT_UNITS.get(clean_unit, 1.0)
        val *= multiplier
    return val


def is_vc_fund_raising(text: str) -> bool:
    """Detect if the text is reporting a venture capital firm raising an investment fund."""
    return bool(_VC_FUND_CONTEXT.search(text))


def extract_funding_amount(text: str) -> Optional[ParsedAmount]:
    """
    Extract and parse the primary funding round amount from text.
    Handles USD, INR, EUR, GBP and undisclosed rounds.
    Guards against VC fund announcements and valuation metrics.
    """
    if not text:
        return None

    # Check for VC fund raising first
    if is_vc_fund_raising(text):
        match = _AMOUNT_REGEX.search(text)
        if match:
            raw = match.group(0).strip()
            return ParsedAmount(
                raw_text=raw,
                evidence=text[:200],
                is_vc_fund_raise=True,
            )

    # Check for undisclosed
    undisclosed_match = _UNDISCLOSED_REGEX.search(text)
    if undisclosed_match:
        return ParsedAmount(
            raw_text=undisclosed_match.group(0).strip(),
            amount=None,
            currency=None,
            is_undisclosed=True,
            evidence=text[max(0, undisclosed_match.start() - 20) : min(len(text), undisclosed_match.end() + 20)],
        )

    # Find amount matches
    for match in _AMOUNT_REGEX.finditer(text):
        start, end = match.start(), match.end()
        raw = match.group(0).strip()

        # Check surrounding sentence for valuation, revenue, AUM, or preceding cumulative total false-positives
        surrounding = text[max(0, start - 65) : min(len(text), end + 65)]
        before_immediate = text[max(0, start - 40) : start]
        after_immediate = text[end : min(len(text), end + 25)]
        if (
            _VALUATION_REVENUE_CONTEXT.search(surrounding)
            or _PRECEDING_TOTAL_CONTEXT_RE.search(before_immediate)
            or _IMMEDIATE_NON_ROUND_SUFFIX_RE.search(after_immediate)
        ):
            continue

        prefix_curr = match.group("prefix_curr")
        suffix_curr = match.group("suffix_curr")
        raw_curr = prefix_curr or suffix_curr or ""
        curr = normalize_currency(raw_curr)

        num_str = match.group("number") or match.group("number_alt")
        unit_str = match.group("unit") or match.group("unit_alt")

        try:
            val = parse_numeric_amount(num_str, unit_str)
        except (ValueError, TypeError):
            continue

        return ParsedAmount(
            raw_text=raw,
            amount=val,
            currency=curr,
            is_undisclosed=False,
            evidence=surrounding.strip(),
        )

    return None
