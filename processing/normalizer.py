"""
processing/normalizer.py
========================
Normalization utilities for company names, websites, and text fields.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse
from typing import Optional


# Corporate entity suffixes to remove when normalizing company names
_LEGAL_SUFFIXES = re.compile(
    r"\b(?:inc\.?|incorporated|llc\.?|ltd\.?|limited|pvt\.?\s+ltd\.?|private\s+limited|corp\.?|corporation|technologies|tech|solutions|platform|group)\b"
    r"|\.(?:club|io|ai|co|com|in)\b",
    re.IGNORECASE,
)


def normalize_company_name(name: str) -> str:
    """
    Produce canonical normalized company name:
    - Lowercase
    - Remove legal suffixes (Inc, LLC, Pvt Ltd, etc.)
    - Remove punctuation
    - Collapse extra whitespace
    """
    if not name:
        return ""

    clean = name.strip().lower()
    clean = _LEGAL_SUFFIXES.sub("", clean)
    clean = re.sub(r"[^\w\s]", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean or name.strip().lower()


def extract_website_domain(url: Optional[str]) -> Optional[str]:
    """
    Extract standard host domain without 'www.' or protocol:
    e.g. 'https://www.wealthai.io/about?ref=1' -> 'wealthai.io'
    """
    if not url:
        return None

    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        clean_url = f"https://{clean_url}"

    try:
        parsed = urlparse(clean_url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        # Remove port if present
        domain = domain.split(":")[0]
        return domain if "." in domain else None
    except Exception:
        return None
