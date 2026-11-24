"""
extraction/company_extractor.py
===============================
Extracts startup company name, description, website, and tentative location from funding text.

Patterns supported:
- Headline syntax: "<Company> raises $10M Series A..."
- Lead sentence: "<Location>-based <Company>, a <description> provider, has secured..."
- Description extraction: "which develops...", "a provider of...", "an AI platform for..."
- Location extraction: "San Francisco-based", "Bengaluru-based", "New York-headquartered"
- Distinguishes recipient startup from venture capital investors.
"""

from __future__ import annotations

import re
from typing import Optional
from pydantic import BaseModel


class ExtractedCompany(BaseModel):
    name: str
    description: Optional[str] = None
    website: Optional[str] = None
    headquarters_city: Optional[str] = None
    headquarters_country: Optional[str] = None
    evidence: str = ""


# Headline pattern: "[Company] (raises|bags|secures|closes|lands) [amount/round]..."
_HEADLINE_PATTERN = re.compile(
    r"^(?:Exclusive:\s*|Report:\s*|(?:Fintech|Wealthtech|Private\s+equity|Private\s+credit|Alternative\s+investment|Investment|AI)\s+(?:startup|platform|firm|company|app)\s+)?"
    r"(?P<company>[A-Z0-9][A-Za-z0-9\.\s&-]{1,35}?)\s+"
    r"(?:raises?|raised|bags?|bagged|secures?|secured|closes?|closed|lands?|snags?|picks\s+up|captures?|captured|scores?|scored|pulls\s+in|nets?|nets\s+in|rakes\s+in|banks|takes\s+in|hauls\s+in)\s+"
    r"(?:a\s+|an\s+)?(?:\$[\d.]+|₹[\d.]+|INR|USD|EUR|GBP|€|£|Rs\.?|undisclosed|\d+\s*(?:million|crore|cr|lakh|bn|billion)|fresh\s+capital|Series|Seed|Pre-seed|funding|investment|capital|venture\s+debt)",
    re.IGNORECASE,
)

# Location pattern: "San Francisco-based", "Bengaluru-based", "New York headquartered"
_LOCATION_PATTERN = re.compile(
    r"\b(?P<city>San Francisco|New York|Bengaluru|Bangalore|Mumbai|Delhi|Gurugram|Gurgaon|Noida|Pune|Hyderabad|Chennai|Austin|Boston|Seattle|Chicago|Los Angeles|Palo Alto|Sunnyvale)\s*(?:-|–|\s+)(?:based|headquartered)\b",
    re.IGNORECASE,
)

# Appositive description: "[Company], which provides ...," or "[Company], an alternative investment platform, ..."
_DESCRIPTION_PATTERN = re.compile(
    r"(?P<company>[A-Z][A-Za-z0-9\s]{1,30}),\s+(?:an?|the|which)\s+(?P<desc>[^,\.]{15,180}?)(?:,\s*has\s+|\s+has\s+raised|\s+announced)",
    re.IGNORECASE,
)

# Website regex
_WEBSITE_REGEX = re.compile(
    r"\b(?:https?://)?(?:www\.)?([a-zA-Z0-9][-a-zA-Z0-9]*\.(?:com|io|ai|co|in|tech|finance|capital|fund))\b",
    re.IGNORECASE,
)

# Known Indian cities for quick country attribution
_INDIAN_CITIES = {"bengaluru", "bangalore", "mumbai", "delhi", "new delhi", "gurugram", "gurgaon", "noida", "pune", "hyderabad", "chennai"}
# Known US cities
_US_CITIES = {"san francisco", "new york", "austin", "boston", "seattle", "chicago", "los angeles", "palo alto", "sunnyvale"}


def extract_company_from_title(title: str) -> Optional[tuple[str, str]]:
    """
    Extract company name from funding announcement title.
    Returns (company_name, evidence).
    """
    if not title:
        return None

    match = _HEADLINE_PATTERN.match(title.strip())
    if match:
        name = match.group("company").strip()
        # Clean up any residual words
        name = re.sub(r"\b(startup|fintech|wealthtech|firm|inc|corp|platform|company)\b", "", name, flags=re.IGNORECASE).strip()
        name = re.sub(r"^(?:and|the|a|an)\s+", "", name, flags=re.IGNORECASE).strip()
        if len(name) >= 2 and not name.lower().startswith(("how", "why", "what", "where", "who")):
            return name, match.group(0)

    # Secondary pattern: "... funding for [Company]"
    sec_match = re.search(r"\b(?:funding\s+for|investment\s+in)\s+([A-Z0-9][A-Za-z0-9\s&-]{1,30})\b", title)
    if sec_match:
        name = sec_match.group(1).strip()
        name = re.sub(r"^(?:and|the|a|an)\s+", "", name, flags=re.IGNORECASE).strip()
        return name, sec_match.group(0)

    return None


def extract_location(text: str) -> tuple[Optional[str], Optional[str]]:
    """
    Extract city and country from text.
    Returns (city, country).
    """
    if not text:
        return None, None

    match = _LOCATION_PATTERN.search(text)
    if match:
        city_raw = match.group("city").strip()
        city_lower = city_raw.lower()
        if city_lower in _INDIAN_CITIES:
            # Canonicalize Bangalore -> Bengaluru
            canonical_city = "Bengaluru" if city_lower == "bangalore" else city_raw.title()
            return canonical_city, "India"
        elif city_lower in _US_CITIES:
            return city_raw.title(), "United States"

    # Explicit country check
    if re.search(r"\b(?:India|Indian startup)\b", text, re.IGNORECASE):
        return None, "India"
    if re.search(r"\b(?:United States|US startup|Silicon Valley|U\.S\.)\b", text, re.IGNORECASE):
        return None, "United States"

    return None, None


def extract_company_info(
    title: str,
    text: Optional[str] = None,
) -> Optional[ExtractedCompany]:
    """
    Main extraction function for company name, location, and description.
    """
    combined_text = f"{title}\n{text or ''}"

    # Extract company name
    comp_title = extract_company_from_title(title)
    company_name = None
    evidence = ""

    if comp_title:
        company_name, evidence = comp_title
    else:
        # Fallback to description regex in first paragraph
        lead_match = _DESCRIPTION_PATTERN.search(text or "")
        if lead_match:
            company_name = lead_match.group("company").strip()
            evidence = lead_match.group(0)

    if not company_name:
        return None

    # Strip leading conjunctions/articles e.g. "and Motilal Oswal" -> "Motilal Oswal"
    company_name = re.sub(r"^(?:and|the|a|an)\s+", "", company_name.strip(), flags=re.IGNORECASE)

    # Extract location
    city, country = extract_location(combined_text[:1000])

    # Extract description
    description = None
    desc_match = _DESCRIPTION_PATTERN.search(text or "")
    if desc_match and desc_match.group("desc"):
        description = desc_match.group("desc").strip()

    # Extract website
    website = None
    for web_match in _WEBSITE_REGEX.finditer(text or ""):
        domain = web_match.group(1).lower()
        # Exclude media websites
        if domain not in ("techcrunch.com", "inc42.com", "yourstory.com", "economictimes.com", "bloomberg.com", "reuters.com"):
            website = f"https://{domain}"
            break

    return ExtractedCompany(
        name=company_name,
        description=description,
        website=website,
        headquarters_city=city,
        headquarters_country=country,
        evidence=evidence,
    )
