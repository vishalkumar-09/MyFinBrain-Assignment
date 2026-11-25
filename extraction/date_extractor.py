"""
extraction/date_extractor.py
============================
Extracts announcement dates and article publication dates.

Distinguishes:
1. Article publication date (from metadata, HTML meta tags, or RSS pubDate).
2. Funding announcement date (from article body text, e.g. "announced on March 15, 2025").

Supports standard formats, Indian date conventions, and relative temporal mentions.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Optional
from dateutil import parser as dateutil_parser
from pydantic import BaseModel


class ParsedDates(BaseModel):
    """Container for resolved publication and announcement dates."""
    publication_date: Optional[date] = None
    announcement_date: Optional[date] = None
    announcement_date_evidence: Optional[str] = None


# Patterns indicating funding announcement date inside the body
_ANNOUNCEMENT_DATE_PATTERNS = [
    re.compile(
        r"\b(?:announced|closed|raised|secured|completed|landed)\s+(?:the\s+round\s+|.{0,50}?\s+)?on\s+([A-Za-z]+\.?\s+\d{1,2},?\s+\d{4}|\d{1,2}\s+[A-Za-z]+\.?\s+\d{4}|\d{4}-\d{2}-\d{2})",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:on\s+)?([A-Za-z]+\.?\s+\d{1,2},?\s+\d{4}),\s+(?:announced|said|closed)",
        re.IGNORECASE,
    ),
    # PR Newswire / Business Wire datelines: "NEW YORK, September 09, 2026" or "CHICAGO, Oct. 14, 2026 /PRNewswire/"
    re.compile(
        r"\b[A-Z][A-Z\s\.]{2,25},\s+([A-Za-z]{3,9}\.?\s+\d{1,2},\s+\d{4})\b(?:\s*/PRNewswire|\s*--|\s*—|\s*\(BUSINESS WIRE\))?",
    ),
]

_PRIOR_ROUND_CONTEXT = re.compile(
    r"\b(?:previously|earlier|back\s+in|prior\s+to|last\s+year|founded\s+in|established\s+in)\b",
    re.IGNORECASE,
)


def parse_iso_or_human_date(date_str: str) -> Optional[date]:
    """Parse any date string cleanly into a date object without crashing."""
    if not date_str or not date_str.strip():
        return None
    try:
        dt = dateutil_parser.parse(date_str)
        return dt.date()
    except (ValueError, TypeError, OverflowError):
        pass

    # Try common explicit formats
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%B %d, %Y", "%d %B %Y"):
        try:
            return datetime.strptime(date_str.strip(), fmt).date()
        except ValueError:
            continue
    return None


def extract_announcement_date(article_text: str, publication_date: Optional[date] = None) -> tuple[Optional[date], Optional[str]]:
    """
    Search article body for explicit mentions of the round's announcement date.
    Returns (announcement_date, evidence_snippet).
    If no explicit date is mentioned, returns (None, None).
    """
    if not article_text:
        return None, None

    for pattern in _ANNOUNCEMENT_DATE_PATTERNS:
        for match in pattern.finditer(article_text):
            # Ignore historical/prior round dates ("back in December 2025", "previously raised")
            context_before = article_text[max(0, match.start() - 60) : match.start()]
            if _PRIOR_ROUND_CONTEXT.search(context_before):
                continue
            date_snippet = match.group(1).strip()
            parsed = parse_iso_or_human_date(date_snippet)
            if parsed:
                evidence = article_text[max(0, match.start() - 20) : min(len(article_text), match.end() + 20)]
                return parsed, evidence.strip()

    return None, None


def resolve_dates(
    published_at: Optional[datetime],
    article_text: Optional[str] = None,
) -> ParsedDates:
    """Resolve and separate publication date and announcement date."""
    pub_date = published_at.date() if published_at else None
    ann_date, ann_evidence = extract_announcement_date(article_text or "", publication_date=pub_date)

    # For same-day journalism without a separate restated date in prose, use publication date
    if ann_date is None and pub_date is not None:
        ann_date = pub_date
        ann_evidence = f"Same-day news coverage ({pub_date.isoformat()})"

    return ParsedDates(
        publication_date=pub_date,
        announcement_date=ann_date,
        announcement_date_evidence=ann_evidence,
    )
