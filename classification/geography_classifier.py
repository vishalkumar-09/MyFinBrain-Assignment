"""
classification/geography_classifier.py
======================================
Geography verification engine for US and Indian startup qualification.

Rules enforced:
1. Target geographies: United States, India.
2. Filter based strictly on headquarters location.
3. NEVER infer headquarters from:
   - Article publisher origin (e.g. Inc42 writing about a US company)
   - Investor location (e.g. US VC investing in an Indian startup)
   - Founder nationality
   - Incidental geographic mentions
4. Mark company NEEDS_REVIEW if headquarters cannot be verified with high confidence.
5. Cross-border operation: Allow companies headquartered in one target country to operate
   in the other without exclusion.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from config.settings import TARGET_COUNTRIES


class GeoStatus(str, Enum):
    VERIFIED = "VERIFIED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class GeographyVerificationResult(BaseModel):
    headquarters_country: Optional[str] = None
    headquarters_city: Optional[str] = None
    operating_countries: list[str] = Field(default_factory=list)
    status: GeoStatus = GeoStatus.NEEDS_REVIEW
    confidence: float = 0.0
    reasoning: str = ""
    evidence: Optional[str] = None


# Explicit headquarters patterns
_HQ_PATTERNS = [
    # "headquartered in San Francisco", "headquartered in Bengaluru, India"
    re.compile(
        r"\bheadquartered\s+in\s+(?P<location>[A-Za-z\s,]{3,40}?)(?:\.|\;|\,|\s+and|\s+with)",
        re.IGNORECASE,
    ),
    # "San Francisco-based", "Mumbai-based"
    re.compile(
        r"\b(?P<city>San Francisco|New York|Bengaluru|Bangalore|Mumbai|Delhi|New Delhi|Gurugram|Gurgaon|Noida|Pune|Hyderabad|Chennai|Austin|Boston|Seattle|Chicago|Los Angeles|Palo Alto|Sunnyvale|Menlo Park)\s*(?:-|–|\s+)(?:based|headquartered)\b",
        re.IGNORECASE,
    ),
    # "startup based in India", "company based in the US"
    re.compile(
        r"\b(?:startup|company|platform|firm)\s+based\s+in\s+(?P<country>India|the\s+United\s+States|the\s+US|the\s+U\.S\.)\b",
        re.IGNORECASE,
    ),
]

_INDIAN_METROS = {
    "bengaluru": "Bengaluru",
    "bangalore": "Bengaluru",
    "mumbai": "Mumbai",
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "gurugram": "Gurugram",
    "gurgaon": "Gurugram",
    "noida": "Noida",
    "pune": "Pune",
    "hyderabad": "Hyderabad",
    "chennai": "Chennai",
    "ahmedabad": "Ahmedabad",
    "kolkata": "Kolkata",
}

_US_METROS = {
    "san francisco": "San Francisco",
    "new york": "New York",
    "austin": "Austin",
    "boston": "Boston",
    "seattle": "Seattle",
    "chicago": "Chicago",
    "los angeles": "Los Angeles",
    "palo alto": "Palo Alto",
    "sunnyvale": "Sunnyvale",
    "menlo park": "Menlo Park",
    "mountain view": "Mountain View",
    "miami": "Miami",
    "denver": "Denver",
}

_OUT_OF_SCOPE_COUNTRIES = {
    "uk": "United Kingdom",
    "united kingdom": "United Kingdom",
    "london": "United Kingdom",
    "germany": "Germany",
    "berlin": "Germany",
    "france": "France",
    "paris": "France",
    "singapore": "Singapore",
    "israel": "Israel",
    "tel aviv": "Israel",
    "canada": "Canada",
    "toronto": "Canada",
    "australia": "Australia",
    "sydney": "Australia",
}


class GeographyClassifier:
    """
    Verifies company headquarters country and city against US and India target scope.
    """

    def verify(
        self,
        company_name: str,
        extracted_city: Optional[str] = None,
        extracted_country: Optional[str] = None,
        article_text: Optional[str] = None,
    ) -> GeographyVerificationResult:
        """
        Verify company geography based strictly on headquarters evidence.
        """
        text = article_text or ""
        evidence_found = ""
        resolved_city = extracted_city
        resolved_country = extracted_country

        # Check explicit HQ regex in text
        for pat in _HQ_PATTERNS:
            match = pat.search(text)
            if match:
                evidence_found = match.group(0)
                if "city" in match.groupdict() and match.group("city"):
                    raw_city = match.group("city").strip().lower()
                    if raw_city in _INDIAN_METROS:
                        resolved_city = _INDIAN_METROS[raw_city]
                        resolved_country = "India"
                    elif raw_city in _US_METROS:
                        resolved_city = _US_METROS[raw_city]
                        resolved_country = "United States"
                elif "location" in match.groupdict() and match.group("location"):
                    raw_loc = match.group("location").strip().lower()
                    for m_key, m_val in _INDIAN_METROS.items():
                        if m_key in raw_loc:
                            resolved_city = m_val
                            resolved_country = "India"
                            break
                    if not resolved_country:
                        for m_key, m_val in _US_METROS.items():
                            if m_key in raw_loc:
                                resolved_city = m_val
                                resolved_country = "United States"
                                break
                    if not resolved_country:
                        if "india" in raw_loc:
                            resolved_country = "India"
                        elif any(term in raw_loc for term in ["us", "u.s.", "united states", "america"]):
                            resolved_country = "United States"
                elif "country" in match.groupdict() and match.group("country"):
                    raw_c = match.group("country").lower()
                    resolved_country = "India" if "india" in raw_c else "United States"
                break

        # Check out of scope locations
        if not resolved_country and text:
            for loc_key, country_name in _OUT_OF_SCOPE_COUNTRIES.items():
                if re.search(rf"\b{re.escape(loc_key)}\s*-(?:based|headquartered)\b", text, re.IGNORECASE):
                    return GeographyVerificationResult(
                        headquarters_country=country_name,
                        status=GeoStatus.OUT_OF_SCOPE,
                        confidence=0.85,
                        reasoning=f"Headquartered in {country_name}, outside US & India target scope.",
                        evidence=f"{loc_key}-based",
                    )

        # Cross-border operations check
        operating = []
        if resolved_country == "United States" and re.search(r"\b(?:operat(?:es|ing)\s+in\s+India|India\s+operations|expansion\s+into\s+India)\b", text, re.IGNORECASE):
            operating.append("India")
        elif resolved_country == "India" and re.search(r"\b(?:operat(?:es|ing)\s+in\s+the\s+US|US\s+office|expansion\s+into\s+the\s+US)\b", text, re.IGNORECASE):
            operating.append("United States")

        # Resolve qualification
        if resolved_country in TARGET_COUNTRIES:
            confidence = 0.90 if resolved_city else 0.75
            return GeographyVerificationResult(
                headquarters_country=resolved_country,
                headquarters_city=resolved_city,
                operating_countries=operating,
                status=GeoStatus.VERIFIED,
                confidence=confidence,
                reasoning=f"Verified headquarters in {resolved_country}" + (f" ({resolved_city})" if resolved_city else ""),
                evidence=evidence_found or f"{resolved_country} mention",
            )

        # Inconclusive
        return GeographyVerificationResult(
            headquarters_country=resolved_country,
            headquarters_city=resolved_city,
            status=GeoStatus.NEEDS_REVIEW,
            confidence=0.3,
            reasoning="Headquarters location could not be verified with definitive evidence.",
            evidence=None,
        )
