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
_CITY_LIST = (
    "San Francisco|New York|New York City|Jersey City|Indianapolis|Bengaluru|Bangalore|"
    "Mumbai|Delhi|New Delhi|Gurugram|Gurgaon|Noida|Greater Noida|Pune|Hyderabad|Chennai|"
    "Ahmedabad|Kolkata|Jaipur|Chandigarh|Kochi|Cochin|Indore|Bhopal|Surat|Vadodara|Baroda|"
    "Coimbatore|Lucknow|Goa|Thiruvananthapuram|Trivandrum|Austin|Boston|Seattle|Chicago|"
    "Los Angeles|Palo Alto|Sunnyvale|Menlo Park|Mountain View|San Jose|Santa Clara|San Mateo|"
    "Redwood City|Santa Monica|Berkeley|Oakland|San Diego|Miami|Denver|Boulder|Atlanta|Dallas|"
    "Houston|Washington, D.C.|Washington DC|Washington|Arlington|Bethesda|McLean|Reston|"
    "Philadelphia|Pittsburgh|Raleigh|Charlotte|Salt Lake City|Nashville|Minneapolis|Portland|"
    "Stamford|Greenwich|Hoboken|Princeton|Cambridge|Columbus|Phoenix|Scottsdale|Reno|Wilmington|"
    "Navi Mumbai|Thane|Faridabad|Mohali|Bhubaneswar|Visakhapatnam|Nagpur|Mysuru|Mangaluru"
)

_HQ_PATTERNS = [
    # "headquartered in San Francisco", "based in Bengaluru, India"
    re.compile(
        r"\b(?:headquartered\s+in|based\s+in|based\s+out\s+of|operating\s+out\s+of|located\s+in)\s+(?P<location>[A-Za-z\s,\.]{3,45}?)(?:\.|\;|\s+and|\s+with|\s+closed|\s+raised|$)",
        re.IGNORECASE,
    ),
    # "San Francisco-based", "Mumbai-based", "London-based", "The Zürich-headquartered company", "Copenhagen-founded"
    re.compile(
        rf"\b(?P<city>{_CITY_LIST}|London|Toronto|Vancouver|Montreal|Singapore|Berlin|Munich|Paris|Zurich|Zürich|Geneva|Tel Aviv|Dubai|Dublin|Amsterdam|Copenhagen|Luxembourg|Stockholm|Oslo|Helsinki|Sydney|Melbourne|Tokyo|Seoul|Hong Kong)\s*(?:-|–|\s+)(?:based|headquartered|founded)\b",
        re.IGNORECASE,
    ),
    # "The Jersey City startup", "A New York startup"
    re.compile(
        rf"\b(?:the|a|an)\s+(?P<city>{_CITY_LIST})\s+(?:startup|company|platform|firm|fintech|wealthtech)\b",
        re.IGNORECASE,
    ),
    # "startup based in India", "company based in the US", "in the United Kingdom"
    re.compile(
        r"\b(?:startup|company|platform|firm|fintech|wealthtech)\s+(?:based|headquartered|founded)\s+in\s+(?P<country>India|the\s+United\s+States|the\s+US|the\s+U\.S\.|the\s+UK|the\s+United\s+Kingdom|Canada|Singapore|Germany|France|Switzerland|Denmark|Luxembourg|Sweden|Ireland|Netherlands)\b",
        re.IGNORECASE,
    ),
    # PR Wire / Indian wire leading datelines: "CHICAGO, Oct. 14, 2026" or "SAN FRANCISCO and NEW YORK, Nov. 17, 2026"
    re.compile(
        r"^(?P<dateline_city>NEW YORK|SAN FRANCISCO|CHICAGO|BOSTON|AUSTIN|SEATTLE|MIAMI|LOS ANGELES|INDIANAPOLIS|ATLANTA|DALLAS|DENVER|JERSEY CITY|WASHINGTON|RENO|MUMBAI|BENGALURU|BANGALORE|NEW DELHI|DELHI|GURUGRAM|HYDERABAD|CHENNAI|PUNE|KOLKATA)(?:\s+and\s+[A-Z ]{3,20})?(?:,\s+[A-Z]{2,4}\b|,\s+[A-Za-z]{3,9}\.?\s+\d{1,2}|\s*:)",
        re.MULTILINE,
    ),
]

_INDIAN_METROS = {
    "bengaluru": "Bengaluru",
    "bangalore": "Bengaluru",
    "mumbai": "Mumbai",
    "bombay": "Mumbai",
    "delhi": "Delhi",
    "new delhi": "Delhi",
    "gurugram": "Gurugram",
    "gurgaon": "Gurugram",
    "noida": "Noida",
    "greater noida": "Greater Noida",
    "pune": "Pune",
    "hyderabad": "Hyderabad",
    "chennai": "Chennai",
    "madras": "Chennai",
    "ahmedabad": "Ahmedabad",
    "kolkata": "Kolkata",
    "calcutta": "Kolkata",
    "jaipur": "Jaipur",
    "chandigarh": "Chandigarh",
    "kochi": "Kochi",
    "cochin": "Kochi",
    "indore": "Indore",
    "bhopal": "Bhopal",
    "surat": "Surat",
    "vadodara": "Vadodara",
    "baroda": "Vadodara",
    "coimbatore": "Coimbatore",
    "lucknow": "Lucknow",
    "goa": "Goa",
    "thiruvananthapuram": "Thiruvananthapuram",
    "trivandrum": "Thiruvananthapuram",
    "navi mumbai": "Navi Mumbai",
    "thane": "Thane",
    "faridabad": "Faridabad",
    "mohali": "Mohali",
    "bhubaneswar": "Bhubaneswar",
    "visakhapatnam": "Visakhapatnam",
    "nagpur": "Nagpur",
    "mysuru": "Mysuru",
    "mysore": "Mysuru",
    "mangaluru": "Mangaluru",
}

_US_METROS = {
    "san francisco": "San Francisco",
    "new york": "New York",
    "new york city": "New York",
    "nyc": "New York",
    "jersey city": "Jersey City",
    "indianapolis": "Indianapolis",
    "austin": "Austin",
    "boston": "Boston",
    "seattle": "Seattle",
    "chicago": "Chicago",
    "los angeles": "Los Angeles",
    "palo alto": "Palo Alto",
    "sunnyvale": "Sunnyvale",
    "menlo park": "Menlo Park",
    "mountain view": "Mountain View",
    "san jose": "San Jose",
    "santa clara": "Santa Clara",
    "san mateo": "San Mateo",
    "redwood city": "Redwood City",
    "santa monica": "Santa Monica",
    "berkeley": "Berkeley",
    "oakland": "Oakland",
    "san diego": "San Diego",
    "miami": "Miami",
    "denver": "Denver",
    "boulder": "Boulder",
    "atlanta": "Atlanta",
    "dallas": "Dallas",
    "houston": "Houston",
    "washington": "Washington, D.C.",
    "washington, d.c.": "Washington, D.C.",
    "washington dc": "Washington, D.C.",
    "arlington": "Arlington",
    "bethesda": "Bethesda",
    "mclean": "McLean",
    "reston": "Reston",
    "philadelphia": "Philadelphia",
    "pittsburgh": "Pittsburgh",
    "raleigh": "Raleigh",
    "charlotte": "Charlotte",
    "salt lake city": "Salt Lake City",
    "nashville": "Nashville",
    "minneapolis": "Minneapolis",
    "portland": "Portland",
    "stamford": "Stamford",
    "greenwich": "Greenwich",
    "hoboken": "Hoboken",
    "princeton": "Princeton",
    "cambridge": "Cambridge",
    "columbus": "Columbus",
    "phoenix": "Phoenix",
    "scottsdale": "Scottsdale",
    "reno": "Reno",
    "wilmington": "Wilmington",
}

_OUT_OF_SCOPE_COUNTRIES = {
    "uk": "United Kingdom",
    "the uk": "United Kingdom",
    "united kingdom": "United Kingdom",
    "the united kingdom": "United Kingdom",
    "london": "United Kingdom",
    "germany": "Germany",
    "berlin": "Germany",
    "munich": "Germany",
    "france": "France",
    "paris": "France",
    "singapore": "Singapore",
    "israel": "Israel",
    "tel aviv": "Israel",
    "canada": "Canada",
    "toronto": "Canada",
    "vancouver": "Canada",
    "montreal": "Canada",
    "australia": "Australia",
    "sydney": "Australia",
    "melbourne": "Australia",
    "switzerland": "Switzerland",
    "zurich": "Switzerland",
    "zürich": "Switzerland",
    "geneva": "Switzerland",
    "luxembourg": "Luxembourg",
    "norway": "Norway",
    "oslo": "Norway",
    "finland": "Finland",
    "helsinki": "Finland",
    "belgium": "Belgium",
    "brussels": "Belgium",
    "dubai": "United Arab Emirates",
    "uae": "United Arab Emirates",
    "ireland": "Ireland",
    "dublin": "Ireland",
    "netherlands": "Netherlands",
    "amsterdam": "Netherlands",
    "denmark": "Denmark",
    "copenhagen": "Denmark",
    "sweden": "Sweden",
    "stockholm": "Sweden",
    "japan": "Japan",
    "tokyo": "Japan",
    "south korea": "South Korea",
    "seoul": "South Korea",
    "hong kong": "Hong Kong",
}

_GEO_SKIP_CONTEXT_RE = re.compile(
    r"(?:\bseparate\s+[^\.]{0,45}?\bfunding\s+round\s+(?:in|i\s+n)\b|"
    r"(?:partner|principal|director|managing\s+director|general\s+partner|founder|ceo)\s+(?:at|of)\s+|"
    r"(?:investor|backer|venture\s+(?:firm|partner)|capital\s+partner)\s+)",
    re.IGNORECASE,
)

_GEO_SKIP_SUFFIX_RE = re.compile(
    r"^(?:\s*(?:-|–|\s+)(?:based|headquartered))?\s+(?:venture\s+capital|vc|private\s+equity|"
    r"investment|growth\s+equity|aerospace|defence|defense|[A-Z][a-z]+\s+[A-Z][a-z]+\s+of)\b",
    re.IGNORECASE,
)

_OOS_DATELINE_RE = re.compile(
    r"^(?:STOCKHOLM|LONDON|ZURICH|ZÜRICH|BERLIN|MUNICH|PARIS|TORONTO|SINGAPORE|COPENHAGEN|DUBLIN|AMSTERDAM|LUXEMBOURG|TEL AVIV)\b",
    re.MULTILINE,
)

_OOS_CITY_MAP = {
    "STOCKHOLM": "Sweden",
    "LONDON": "United Kingdom",
    "ZURICH": "Switzerland",
    "ZÜRICH": "Switzerland",
    "BERLIN": "Germany",
    "MUNICH": "Germany",
    "PARIS": "France",
    "TORONTO": "Canada",
    "SINGAPORE": "Singapore",
    "COPENHAGEN": "Denmark",
    "DUBLIN": "Ireland",
    "AMSTERDAM": "Netherlands",
    "LUXEMBOURG": "Luxembourg",
    "TEL AVIV": "Israel",
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

        if resolved_city:
            raw_c = resolved_city.strip().lower()
            if raw_c in _INDIAN_METROS:
                resolved_city = _INDIAN_METROS[raw_c]
                if not resolved_country:
                    resolved_country = "India"
            elif raw_c in _US_METROS:
                resolved_city = _US_METROS[raw_c]
                if not resolved_country:
                    resolved_country = "United States"

        # Check explicit HQ regex in text, picking EARLIEST valid HQ match so lead OOS/HQ beats later investor cities
        oos_dl = _OOS_DATELINE_RE.search(text[:1000]) if text else None
        candidates: list[tuple[int, re.Match]] = []
        for pat in _HQ_PATTERNS:
            for match in pat.finditer(text):
                prefix_win = text[max(0, match.start() - 65) : match.start()]
                suffix_win = text[match.end() : min(len(text), match.end() + 45)]
                if _GEO_SKIP_CONTEXT_RE.search(prefix_win) or _GEO_SKIP_SUFFIX_RE.match(suffix_win):
                    continue
                candidates.append((match.start(), match))
        candidates.sort(key=lambda item: item[0])

        if oos_dl and (not candidates or oos_dl.start() < candidates[0][0]):
            ctry = _OOS_CITY_MAP.get(oos_dl.group(0).upper(), "International")
            return GeographyVerificationResult(
                headquarters_country=ctry,
                status=GeoStatus.OUT_OF_SCOPE,
                confidence=0.85,
                reasoning=f"Headquartered in {ctry} (dateline), outside US & India target scope.",
                evidence=oos_dl.group(0),
            )

        for _, match in candidates:
            evidence_found = match.group(0)
            if "dateline_city" in match.groupdict() and match.group("dateline_city"):
                raw_dc = match.group("dateline_city").strip().lower()
                if raw_dc in _INDIAN_METROS:
                    resolved_city = _INDIAN_METROS[raw_dc]
                    resolved_country = "India"
                elif raw_dc in _US_METROS:
                    resolved_city = _US_METROS[raw_dc]
                    resolved_country = "United States"
                if resolved_country:
                    break
            elif "city" in match.groupdict() and match.group("city"):
                raw_city = match.group("city").strip().lower()
                if raw_city in _OUT_OF_SCOPE_COUNTRIES:
                    country_name = _OUT_OF_SCOPE_COUNTRIES[raw_city]
                    return GeographyVerificationResult(
                        headquarters_country=country_name,
                        status=GeoStatus.OUT_OF_SCOPE,
                        confidence=0.85,
                        reasoning=f"Headquartered in {country_name}, outside US & India target scope.",
                        evidence=evidence_found,
                    )
                if raw_city in _INDIAN_METROS:
                    resolved_city = _INDIAN_METROS[raw_city]
                    resolved_country = "India"
                elif raw_city in _US_METROS:
                    resolved_city = _US_METROS[raw_city]
                    resolved_country = "United States"
                if resolved_country:
                    break
            elif "location" in match.groupdict() and match.group("location"):
                raw_loc = match.group("location").strip().lower()
                for loc_key, country_name in _OUT_OF_SCOPE_COUNTRIES.items():
                    if re.search(rf"\b{re.escape(loc_key)}\b", raw_loc):
                        return GeographyVerificationResult(
                            headquarters_country=country_name,
                            status=GeoStatus.OUT_OF_SCOPE,
                            confidence=0.85,
                            reasoning=f"Headquartered in {country_name}, outside US & India target scope.",
                            evidence=evidence_found,
                        )
                for m_key, m_val in _INDIAN_METROS.items():
                    if re.search(rf"\b{re.escape(m_key)}\b", raw_loc):
                        resolved_city = m_val
                        resolved_country = "India"
                        break
                if not resolved_country:
                    for m_key, m_val in _US_METROS.items():
                        if re.search(rf"\b{re.escape(m_key)}\b", raw_loc):
                            resolved_city = m_val
                            resolved_country = "United States"
                            break
                if not resolved_country:
                    if "india" in raw_loc:
                        resolved_country = "India"
                    elif any(term in raw_loc for term in ["united states", "u.s."]):
                        resolved_country = "United States"
                if resolved_country:
                    break
            elif "country" in match.groupdict() and match.group("country"):
                raw_c = match.group("country").lower()
                for loc_key, country_name in _OUT_OF_SCOPE_COUNTRIES.items():
                    if loc_key in raw_c:
                        return GeographyVerificationResult(
                            headquarters_country=country_name,
                            status=GeoStatus.OUT_OF_SCOPE,
                            confidence=0.85,
                            reasoning=f"Headquartered in {country_name}, outside US & India target scope.",
                            evidence=evidence_found,
                        )
                resolved_country = "India" if "india" in raw_c else "United States"
                break

        # Check out of scope locations in broader text if still unresolved
        if not resolved_country and text:
            for loc_key, country_name in _OUT_OF_SCOPE_COUNTRIES.items():
                if re.search(rf"\b{re.escape(loc_key)}\s*(?:-|–|\s+)(?:based|headquartered|founded)\b", text, re.IGNORECASE):
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
