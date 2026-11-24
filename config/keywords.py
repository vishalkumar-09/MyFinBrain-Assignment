"""
config/keywords.py
==================
All keyword lists used for discovery query generation.
Adding a new keyword here automatically propagates it to all query builders
without touching any other module.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Business domain keywords
# ---------------------------------------------------------------------------
BUSINESS_KEYWORDS: list[str] = [
    "private markets",
    "private equity",
    "private credit",
    "private debt",
    "private market infrastructure",
    "pre-IPO",
    "secondary markets",
    "unlisted shares",
    "private investment platform",
    "private market portfolio management",
    "private market analytics",
    "alternative investments",
    "alternative asset management",
    "fractional ownership",
    "real estate investment platform",
    "alternative investment marketplace",
    "hedge fund technology",
    "commodities investment",
    "collectibles investment",
    "alternative asset portfolio",
    "infrastructure investment platform",
    "wealth management",
    "digital wealth management",
    "wealthtech",
    "investment advisory",
    "portfolio management",
    "family office",
    "asset management technology",
    "financial planning platform",
    "investment management platform",
    "digital brokerage",
    "personalized investment",
    "investment infrastructure",
    "portfolio analytics",
    "family office software",
    "private market data",
    "asset allocation technology",
    "investment research platform",
    "financial advisory",
]

# ---------------------------------------------------------------------------
# Funding event keywords
# ---------------------------------------------------------------------------
FUNDING_KEYWORDS: list[str] = [
    "raises funding",
    "raised funding",
    "secures funding",
    "secured funding",
    "secured investment",
    "Series A",
    "Series B",
    "Series C",
    "Series D",
    "seed round",
    "pre-seed",
    "angel round",
    "angel investment",
    "venture capital",
    "venture debt",
    "funding round",
    "bags investment",
    "strategic investment",
    "bridge round",
    "growth round",
    "investment round",
    "closes round",
    "completes funding",
    "announces funding",
]

# ---------------------------------------------------------------------------
# Country-specific qualifiers
# ---------------------------------------------------------------------------
GEO_QUALIFIERS: dict[str, list[str]] = {
    "United States": ["US startup", "American startup", "Silicon Valley", "New York startup"],
    "India": ["Indian startup", "India startup", "Bengaluru startup", "Mumbai startup", "Delhi startup"],
}

# ---------------------------------------------------------------------------
# Funding stage normalisation map
# Maps raw extracted strings → canonical stage names.
# ---------------------------------------------------------------------------
FUNDING_STAGE_MAP: dict[str, str] = {
    # Pre-seed
    "pre-seed": "Pre-Seed",
    "pre seed": "Pre-Seed",
    "preseed": "Pre-Seed",
    # Angel
    "angel": "Angel",
    "angel round": "Angel",
    "angel investment": "Angel",
    # Seed
    "seed": "Seed",
    "seed round": "Seed",
    "seed funding": "Seed",
    "seed stage": "Seed",
    # Series
    "series a": "Series A",
    "series-a": "Series A",
    "series b": "Series B",
    "series-b": "Series B",
    "series c": "Series C",
    "series-c": "Series C",
    "series d": "Series D",
    "series-d": "Series D",
    "series e": "Series E",
    "series-e": "Series E",
    "series f": "Series F",
    "series-f": "Series F",
    # Growth / Late stage
    "growth": "Growth",
    "growth round": "Growth",
    "growth equity": "Growth",
    "late stage": "Late Stage",
    # Venture Debt
    "venture debt": "Venture Debt",
    "debt financing": "Venture Debt",
    "debt funding": "Venture Debt",
    # Strategic
    "strategic investment": "Strategic",
    "strategic round": "Strategic",
    "strategic funding": "Strategic",
    # Bridge
    "bridge": "Bridge",
    "bridge round": "Bridge",
    "bridge financing": "Bridge",
    # Other
    "undisclosed": "Undisclosed",
    "funding": "Other",
    "investment": "Other",
}

# ---------------------------------------------------------------------------
# Currency symbols / codes → ISO 4217
# ---------------------------------------------------------------------------
CURRENCY_MAP: dict[str, str] = {
    "$": "USD",
    "usd": "USD",
    "us$": "USD",
    "u.s.$": "USD",
    "€": "EUR",
    "eur": "EUR",
    "£": "GBP",
    "gbp": "GBP",
    "₹": "INR",
    "inr": "INR",
    "rs.": "INR",
    "rs": "INR",
    "rupees": "INR",
    "rupee": "INR",
    "¥": "JPY",
    "jpy": "JPY",
    "s$": "SGD",
    "sgd": "SGD",
    "a$": "AUD",
    "aud": "AUD",
    "c$": "CAD",
    "cad": "CAD",
    "aed": "AED",
}

# ---------------------------------------------------------------------------
# Amount unit multipliers
# ---------------------------------------------------------------------------
AMOUNT_UNITS: dict[str, float] = {
    "thousand": 1_000,
    "k": 1_000,
    "million": 1_000_000,
    "mn": 1_000_000,
    "m": 1_000_000,
    "billion": 1_000_000_000,
    "bn": 1_000_000_000,
    "b": 1_000_000_000,
    # Indian system
    "lakh": 100_000,
    "lakhs": 100_000,
    "crore": 10_000_000,
    "crores": 10_000_000,
    "cr": 10_000_000,
    "cr.": 10_000_000,
}
