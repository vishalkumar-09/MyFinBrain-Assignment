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


# Headline pattern: "[Optional Kicker: ] [Optional Adjective/Investor-backed] [Company] (raises|bags|secures|closes|lands) [amount/round]..."
_PREFIX_NOISE_RE = re.compile(
    r"^(?:"
    r"Exclusive:\s*|Update:\s*|\[Update\]\s*|Report:\s*|CORRECTION\s*[–—-]\s*"
    r"|(?:[A-Z][A-Za-z0-9\s\.\-&']+?)-(?:backed|based)\s+"
    r"|Ex-[A-Za-z0-9\s\-]+?(?:\s+directors?'?s?|\s+founded)?\s+"
    r"|(?:Fintech|Wealthtech|WealthTech|Wealth\s+management|Alternative\s+investment|Digital\s+wealth|Private\s+equity|Private\s+credit|Investment|AI\s+investing|AI\s+video(?:\s+production)?|AI-native|AI-powered|AI|Data\s+security|Credit-led\s+fintech|Fintech\s+infra|Fintech\s+and\s+brokerage|Specialty\s+chemicals|Spacetech|Circular\s+economy|Video\s+production|Indian\s+chip|Kerala(?:-based)?|D2C\s+Brand|D2C|Neocloud|Trading|Brokerage|Asset\s+management|Online\s+wealth|Viral\s+AI|Deep-?tech|Cleantech|Insurtech|PropTech|RegTech|IPO-bound)\s+"
    r"(?:startup|platform|firm|company|app|hedge\s+fund|infra(?:structure)?\s+startup|trading\s+platform|brokerage\s+startup|brokerage|maker|business|brand)?\s*"
    r")+",
    re.IGNORECASE,
)

_HEADLINE_PATTERN = re.compile(
    r"^(?P<company>[A-Za-z0-9][A-Za-z0-9\. &\-'/]{1,45}?)\s+"
    r"(?:is\s+raising|to\s+raise|set\s+to\s+raise|plans\s+to\s+raise|eyes|kicks\s+off|raises?|raised|bags?|bagged|secures?|secured|closes?|closed|lands?|snags?|picks\s+up|captures?|captured|scores?|scored|pulls\s+in|nets?|nets\s+in|rakes\s+in|banks|takes\s+in|hauls\s+in)\s+"
    r"(?:a\s+|an\s+|up\s+to\s+|over\s+|about\s+|roughly\s+|nearly\s+)?"
    r"(?:\$[\d.]+|₹[\d.]+|€[\d.]+|£[\d.]+|C\$[\d.]+|A\$[\d.]+|INR|USD|EUR|GBP|Rs\.?|undisclosed|\d+(?:\.\d+)?\s*(?:million|crore|cr|lakh|bn|billion)|fresh\s+capital|strategic\s+capital|strategic\s+funding|new\s+funding|Series|Seed|Pre-seed|funding|investment|capital|venture\s+debt)",
    re.IGNORECASE,
)

# Colon-separated headline (e.g. "From Rs 3,800 Cr...: Angel One-backed Ionic Wealth raises Rs 177 Cr"
# or "Index Industries: $50 Million Seed Funding To Launch...")
_COLON_AMOUNT_HEADLINE = re.compile(
    r"^(?P<company>(?-i:[A-Z0-9][A-Za-z0-9\. &'\-]{1,40}?)):\s*"
    r"(?:Up\s+To\s+|Over\s+)?(?:\$[\d.]+|₹[\d.]+|INR|USD|Rs\.?)\s*[\d.]*\s*(?:Million|Billion|Mn|Cr|Crore|Lakh|M|B)\s+(?:Seed|Pre-Seed|Series\s+[A-F]|Funding|Investment|Financing|Round)\b",
    re.IGNORECASE,
)

# Known Indian cities for quick country attribution
_INDIAN_CITIES = {
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

# Known US cities
_US_CITIES = {
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

# Location patterns
_CITY_OR_REGEX = "|".join(
    re.escape(k.title())
    for k in sorted(list(_INDIAN_CITIES.keys()) + list(_US_CITIES.keys()), key=len, reverse=True)
)

_LOCATION_PATTERN = re.compile(
    rf"\b(?P<city>{_CITY_OR_REGEX})\s*(?:-|–|\s+)(?:based|headquartered)\b",
    re.IGNORECASE,
)

_BASED_IN_PATTERN = re.compile(
    rf"\b(?:headquartered\s+in|based\s+in|based\s+out\s+of|operating\s+out\s+of|located\s+in)\s+(?P<city>{_CITY_OR_REGEX})\b",
    re.IGNORECASE,
)

_CITY_STARTUP_PATTERN = re.compile(
    rf"\b(?:an?|the)\s+(?P<city>{_CITY_OR_REGEX})\s+(?:startup|platform|fintech|company|firm|wealthtech|provider)\b",
    re.IGNORECASE,
)

_CITY_STATE_PATTERN = re.compile(
    rf"\b(?P<city>{_CITY_OR_REGEX}),\s*(?:CA|California|NY|New York|NJ|New Jersey|IN|Indiana|TX|Texas|MA|Massachusetts|WA|Washington|IL|Illinois|FL|Florida|CO|Colorado|GA|Georgia|CT|Connecticut|NV|Nevada|AZ|Arizona|OH|Ohio|DE|Delaware|Karnataka|Maharashtra|Haryana|Telangana|Tamil Nadu|India|U\.S\.|US|USA|D\.C\.)\b",
    re.IGNORECASE,
)

_DATELINE_CITY_PATTERN = re.compile(
    r"^(?P<city>NEW YORK|SAN FRANCISCO|CHICAGO|BOSTON|AUSTIN|SEATTLE|MIAMI|LOS ANGELES|INDIANAPOLIS|ATLANTA|DALLAS|DENVER|JERSEY CITY|WASHINGTON|RENO|MUMBAI|BENGALURU|BANGALORE|NEW DELHI|DELHI|GURUGRAM|HYDERABAD|CHENNAI|PUNE|KOLKATA)(?:\s+and\s+[A-Z ]{3,20})?(?:,\s+[A-Z]{2,4}\b|,\s+[A-Za-z]{3,9}\.?\s+\d{1,2}|\s*:)",
    re.MULTILINE,
)

# Appositive description: "[Company], which provides ...," or "[Company], an alternative investment platform, ..."
# Case-sensitive on <company> so mid-word lowercase fragments cannot match.
_DESCRIPTION_PATTERN = re.compile(
    r"(?:^|(?<=\n)|(?<=[\.\!\?]\s))(?:(?:[A-Za-z\.\- ]{2,25}?-based|Wealth\s+management\s+(?:firm|startup))\s+)?"
    r"(?P<company>(?-i:[A-Z][A-Za-z0-9&\-\. ]{1,35}?)),\s+(?:an?|the|which)\s+"
    r"(?P<desc>[^\.\n]{15,200}?)"
    r"(?:,\s*(?:has|had|is|raises?|raised|secures?|secured|closes?|closed|lands?|bags?|announced)"
    r"|\s+(?:has\s+raised|raised|raises|secured|secures|closed|closes|announced))",
)

# Website regex
_WEBSITE_REGEX = re.compile(
    r"\b(?:https?://)?(?:www\.)?([a-zA-Z0-9][-a-zA-Z0-9]*\.(?:com|io|ai|co|in|tech|finance|capital|fund|club))\b",
    re.IGNORECASE,
)

_FALLBACK_SKIP_TITLE_RE = re.compile(
    r"\b(?:roundup|weekly|daily\s+funding|largest|top\s+\d+|venture\s+capital|funding\s+(?:surged|soars)|"
    r"doubled\s+yoy|in\s+q[1-4]\b|deal\s+activity|projected\s+to\s+(?:decline|grow|reach|hit)|"
    r"may\s+have\s+sold|anthropic\s+shares|"
    r"targets\s+|extends\s+.*platform|unveils\s+|selects\s+|partners\s+with|robotaxis|files\s+drhp|"
    r"private\s+equity\s+pool|credit\s+strategy|to\s+invest\s+in|commits\s+(?:rs|₹|\$|€|£)|definitive\s+agreement)\b",
    re.IGNORECASE,
)

_BAD_FALLBACK_COMPANY_RE = re.compile(
    r"^(?:technology\s+company|company|firm|platform|startup|startups|agreement|portfolio|"
    r"new\s+fundings?|commercial\s+agreement|venture\s+fund)\b"
    r"|\b(?:brought\s+in|when\s+it|if\s+the|portfolio\s+includes|commercial\s+agreement)\b",
    re.IGNORECASE,
)


def _clean_extracted_company_name(raw_name: str) -> str:
    name = re.sub(r"^(?:and|the|a|an)\s+", "", raw_name.strip(), flags=re.IGNORECASE)
    name = re.sub(
        r"^(?:wealth\s+management\s+(?:firm|startup)|based|video\s+production|trading|brokerage|"
        r"circular\s+economy|indian\s+chip|kerala|(?:d2c\s+)?lifestyle\s+(?:brand|startup)|d2c\s+brand|neocloud)\s+",
        "",
        name,
        flags=re.IGNORECASE,
    )
    name = re.sub(r"\b(startup|fintech|wealthtech|inc|corp|platform|company)\b", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+(?:has|had|to|set\s+to|plans\s+to|reportedly|is)$", "", name.strip(), flags=re.IGNORECASE)
    name = re.sub(r"\s+", " ", name).strip(" :-–—,")
    return name


def extract_company_from_title(title: str) -> Optional[tuple[str, str]]:
    """
    Extract company name from funding announcement title.
    Returns (company_name, evidence).
    """
    if not title:
        return None

    clean_title = title.strip()

    # Check colon-prefixed round headlines: e.g. "From X to Y: Angel One-backed Ionic Wealth raises..."
    if ":" in clean_title:
        head, tail = clean_title.split(":", 1)
        tail_stripped = _PREFIX_NOISE_RE.sub("", tail.strip()).strip()
        tail_match = _HEADLINE_PATTERN.match(tail_stripped)
        if tail_match:
            name = _clean_extracted_company_name(tail_match.group("company"))
            if len(name) >= 2 and not name.lower().startswith(("how", "why", "what", "where", "who", "from")):
                return name, tail_match.group(0)

    # Check "[Company]: $X Series..." format before generic noise stripping
    colon_match = _COLON_AMOUNT_HEADLINE.match(clean_title)
    if colon_match:
        name = _clean_extracted_company_name(colon_match.group("company"))
        if len(name) >= 2:
            return name, colon_match.group(0)

    stripped_title = _PREFIX_NOISE_RE.sub("", clean_title).strip()
    for candidate_str in (stripped_title, clean_title):
        match = _HEADLINE_PATTERN.match(candidate_str)
        if match:
            name = _clean_extracted_company_name(match.group("company"))
            if len(name) >= 2 and not name.lower().startswith(("how", "why", "what", "where", "who", "from", "ex-")):
                return name, match.group(0)

    # Secondary pattern: "... funding for [Company]"
    sec_match = re.search(r"\b(?:funding\s+for|investment\s+in)\s+([A-Z0-9][A-Za-z0-9\s&-]{1,30})\b", clean_title)
    if sec_match:
        name = _clean_extracted_company_name(sec_match.group(1))
        if len(name) >= 2:
            return name, sec_match.group(0)

    return None


def _resolve_city_country(city_raw: str) -> tuple[Optional[str], Optional[str]]:
    city_lower = city_raw.lower().strip()
    if city_lower in _INDIAN_CITIES:
        return _INDIAN_CITIES[city_lower], "India"
    elif city_lower in _US_CITIES:
        return _US_CITIES[city_lower], "United States"
    return None, None


_MEDIA_DOMAINS = frozenset({
    "techcrunch.com", "inc42.com", "yourstory.com", "economictimes.com",
    "economictimes.indiatimes.com", "indiatimes.com", "bloomberg.com", "reuters.com",
    "entrackr.com", "fintech.global", "pulse2.com", "alleywatch.com",
    "business-standard.com", "prnewswire.com", "businesswire.com", "yahoo.com",
    "finance.yahoo.com", "cryptobriefing.com", "morningstar.com", "vccircle.com",
    "livemint.com", "moneycontrol.com", "ft.com", "wsj.com", "forbes.com",
    "indianstartupnews.com", "thehindubusinessline.com", "entrepreneur.com",
})

_OUT_OF_SCOPE_HQ_RE = re.compile(
    r"\b(?:London|UK|United Kingdom|Toronto|Canada|Singapore|Berlin|Munich|Germany|Paris|France|"
    r"Z[uü]rich|Switzerland|Tel Aviv|Israel|Dubai|UAE|Dublin|Ireland|Amsterdam|Netherlands|"
    r"Copenhagen|Denmark|Luxembourg|Stockholm|Sweden|Oslo|Norway|Helsinki|Finland|"
    r"Sydney|Australia|Tokyo|Seoul|Hong Kong)\s*(?:-|–|\s+)(?:based|headquartered|founded)\b"
    r"|\b(?:headquartered|based|founded)\s+in\s+(?:London|Toronto|Singapore|Berlin|Munich|Paris|"
    r"Z[uü]rich|Tel Aviv|Dubai|Dublin|Amsterdam|Copenhagen|Luxembourg|Stockholm|Sydney|"
    r"the UK|United Kingdom|Canada|Germany|France|Switzerland)\b",
    re.IGNORECASE,
)

_NON_TARGET_LOC_CONTEXT_RE = re.compile(
    r"(?:\bseparate\s+[^\.]{0,45}?\bfunding\s+round\s+(?:in|i\s+n)\b|"
    r"(?:partner|principal|director|managing\s+director|general\s+partner|founder|ceo)\s+(?:at|of)\s+|"
    r"(?:investor|backer|venture\s+(?:firm|partner)|capital\s+partner)\s+)",
    re.IGNORECASE,
)

_NON_TARGET_LOC_SUFFIX_RE = re.compile(
    r"^(?:\s*(?:-|–|\s+)(?:based|headquartered))?\s+(?:venture\s+capital|vc|private\s+equity|"
    r"investment|growth\s+equity|aerospace|defence|defense|[A-Z][a-z]+\s+[A-Z][a-z]+\s+of)\b",
    re.IGNORECASE,
)


def extract_location(text: str, company_name: Optional[str] = None) -> tuple[Optional[str], Optional[str]]:
    """
    Extract city and country from text.
    Returns (city, country).
    """
    if not text:
        return None, None

    # Guard: if explicit out-of-scope HQ phrase or out-of-scope dateline appears in lead before US/India city mention
    oos_match = _OUT_OF_SCOPE_HQ_RE.search(text[:2000])
    oos_dateline = re.search(
        r"^(?:STOCKHOLM|LONDON|ZURICH|ZÜRICH|BERLIN|MUNICH|PARIS|TORONTO|SINGAPORE|COPENHAGEN|DUBLIN|AMSTERDAM|LUXEMBOURG|TEL AVIV)\b",
        text[:1000],
        re.MULTILINE,
    )
    if oos_dateline and (oos_match is None or oos_dateline.start() < oos_match.start()):
        oos_match = oos_dateline

    # Build prioritized text chunks: paragraphs mentioning company_name first, then full text
    search_chunks: list[str] = []
    if company_name:
        short_key = company_name.split()[0].lower()
        if len(short_key) >= 3:
            matching_paras = [p for p in text.splitlines() if short_key in p.lower() or company_name.lower() in p.lower()]
            if matching_paras:
                search_chunks.append("\n".join(matching_paras))
    search_chunks.append(text)

    for chunk in search_chunks:
        is_full = chunk is text
        # 1. Location patterns in order of specificity
        for pat in (_DATELINE_CITY_PATTERN, _LOCATION_PATTERN, _BASED_IN_PATTERN, _CITY_STATE_PATTERN, _CITY_STARTUP_PATTERN):
            for match in pat.finditer(chunk):
                if is_full and oos_match and oos_match.start() < match.start():
                    return None, None
                # Skip explicit investor/other-company location phrases
                prefix_win = chunk[max(0, match.start() - 65) : match.start()]
                suffix_win = chunk[match.end() : min(len(chunk), match.end() + 45)]
                if _NON_TARGET_LOC_CONTEXT_RE.search(prefix_win) or _NON_TARGET_LOC_SUFFIX_RE.match(suffix_win):
                    continue
                city, country = _resolve_city_country(match.group("city"))
                if city and country:
                    return city, country

    if oos_match:
        return None, None

    # 2. Explicit country check
    if re.search(r"\b(?:Indian startup|India-based|headquartered in India|based in India)\b", text, re.IGNORECASE):
        return None, "India"
    if re.search(r"\b(?:US startup|U\.S\. startup|US-based|U\.S\.-based|headquartered in the United States|based in the United States|based in the US)\b", text, re.IGNORECASE):
        return None, "United States"

    return None, None


def extract_company_info(
    title: str,
    text: Optional[str] = None,
) -> Optional[ExtractedCompany]:
    """
    Main extraction function for company name, location, and description.
    """
    body_text = text or ""
    combined_text = f"{title}\n{body_text}"

    # Extract company name
    comp_title = extract_company_from_title(title)
    company_name = None
    evidence = ""

    if comp_title:
        company_name, evidence = comp_title
    elif not _FALLBACK_SKIP_TITLE_RE.search(title or ""):
        # Fallback to description regex only in opening 1200 chars of genuine deal articles
        lead_match = _DESCRIPTION_PATTERN.search(body_text[:1200])
        if lead_match:
            cand = _clean_extracted_company_name(lead_match.group("company"))
            if (
                cand
                and "\n" not in cand
                and len(cand.split()) <= 5
                and cand[0].isupper()
                and not _BAD_FALLBACK_COMPANY_RE.search(cand)
            ):
                company_name = cand
                evidence = lead_match.group(0)

    if not company_name:
        return None

    # Clean extracted company name consistently
    company_name = _clean_extracted_company_name(company_name) or company_name

    # Extract location across article body (search up to 8000 characters)
    city, country = extract_location(combined_text[:8000], company_name=company_name)

    # Extract description
    description = None
    desc_match = _DESCRIPTION_PATTERN.search(body_text)
    if desc_match and desc_match.group("desc"):
        description = desc_match.group("desc").strip()
    elif body_text:
        # Fallback to clean lead sentence summarizing what the company does
        for line in body_text.splitlines():
            clean_line = line.strip()
            if len(clean_line) >= 40 and clean_line.lower() != (title or "").strip().lower():
                first_sent = re.split(r"(?<=[.!?])\s+", clean_line)[0].strip()
                description = first_sent[:220]
                break

    # Extract website
    website = None
    for web_match in _WEBSITE_REGEX.finditer(body_text):
        domain = web_match.group(1).lower()
        if domain not in _MEDIA_DOMAINS and not any(domain.endswith(f".{m}") for m in _MEDIA_DOMAINS):
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
