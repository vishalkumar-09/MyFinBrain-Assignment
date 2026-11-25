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


# Lead investor regex patterns (no newlines/periods inside captured investor names)
_INV_NAME_CHARS = r"[A-Z0-9][A-Za-z0-9 &'/\-\(\)]{1,75}?(?:\.[A-Za-z]{2,4})?"
_INV_OPT_ROLE_PREFIX = (
    r"(?i:(?:the|its|existing|new|returning)\s+(?:(?:investor|backer|investors|backers)\s+)?|"
    r"(?:global\s+)?(?:venture\s+|vc\s+|investment\s+|private\s+equity\s+)firm\s+|"
    r"asset\s+manager\s+)*"
)
_LEAD_PATTERNS = [
    re.compile(
        rf"\b(?:[Ll]ed|[Cc]o-led)\s+by\s+{_INV_OPT_ROLE_PREFIX}(?P<leads>{_INV_NAME_CHARS}(?:,\s*{_INV_NAME_CHARS})*)(?:\s+with\s+(?:participation|a\s+mix)|\s+and\s+joined|\s+alongside|\s+along\s+with|\s+at\s+a\s+|\s+to\s+|\s+for\s+|\s+as\s+(?:the|it|an)\b|\r|\n|\.|\,|;)",
    ),
    re.compile(
        rf"(?:^|(?<=[\.\!\?\n]\s)|(?<=\n)){_INV_OPT_ROLE_PREFIX}(?P<leads>[A-Z0-9][A-Za-z0-9 &,'\-]{{1,50}}?)\s+(?:[Ll]ed\s+the\s+(?:funding|seed|round|investment|financing|Series\s+[A-Za-z]))",
    ),
    re.compile(
        rf"\b(?:[Ii]nvestment|[Rr]ound|[Ff]inancing)\s+(?:was\s+)?(?:led|co-led)\s+by\s+{_INV_OPT_ROLE_PREFIX}(?P<leads>{_INV_NAME_CHARS}(?:,\s*{_INV_NAME_CHARS})*)(?:\s+with|\s+alongside|\s+for|\s+as\s+|\r|\n|\.|\,|;)",
    ),
    re.compile(
        rf"\b(?:[Ll]ead|[Aa]nchor)\s+[Ii]nvestor\s+(?:was|is)\s+{_INV_OPT_ROLE_PREFIX}(?P<leads>{_INV_NAME_CHARS})(?:\s+with|\s+alongside|\r|\n|\.|\,|;)",
    ),
    re.compile(
        rf"\b(?:[Uu]nder\s+the\s+leadership\s+of|[Ss]pearheaded\s+by)\s+{_INV_OPT_ROLE_PREFIX}(?P<leads>{_INV_NAME_CHARS})(?:\r|\n|\.|\,|;)",
    ),
    re.compile(
        r"\b(?P<leads>[A-Z][A-Za-z0-9\.\-]{1,35})-led\s+(?:Series\s+[A-Z]|seed|funding|round)\b",
    ),
]

# Participating investors patterns
_PARTICIPATING_PATTERNS = [
    re.compile(
        rf"\b(?:(?:with|also\s+saw|saw\s+continued|saw)\s+participation\s+from|joined\s+by|participating\s+investors\s+included?|attracted\s+backing\s+from|backed\s+by|investors?\s+includ(?:ed?|ing)|newly\s+revealed\s+investors\s+are)\s+{_INV_OPT_ROLE_PREFIX}(?P<others>[A-Za-z0-9](?:[^\n\r\.;!?]|(?<=\s[A-Z])\.){{2,180}}?)(?:\.(?<=\w\w\.)|\r|\n|as\s+well\s+as|\s+among\s+others|\s+also|\s+into\s+|\s+to\s+power\b|\s+according\s+to\b|\s+alongside\s+a\s+collection\b)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|(?<=[\.\!\?\n]\s)|(?<=\n))(?P<others>[A-Z][^\n\r\.;!?]{2,140}?)\s+also\s+(?:took\s+part|participated)\b",
    ),
    re.compile(
        rf"\b(?:existing\s+(?:investors|backers)\s+including|other\s+investors\s+(?:included?|were))\s+{_INV_OPT_ROLE_PREFIX}(?P<others>[A-Za-z0-9][^\n\r\.;!?]{{2,140}}?)(?:\.|\r|\n|as\s+well\s+as|\s+among\s+others)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:while|and)\s+(?P<others>[A-Z][^\n\r\.;!?]{2,100}?)\s+(?:is|are)\s+also\s+participating\b",
    ),
    re.compile(
        rf"\b(?:raised|secured|closes|closed|received|obtained|raising|strategic\s+capital)\s+(?:[^\n\r\.]|\.\d){{0,80}}?\bfrom\s+{_INV_OPT_ROLE_PREFIX}(?P<others>[A-Z0-9][^\n\r\.;!?]{{2,140}}?)(?:\.|\r|\n|\s+with\s+|\s+to\s+|\s+at\s+|\s+for\s+|\s+as\s+)",
    ),
]

_PRIOR_ROUND_CONTEXT = re.compile(
    r"\b(?:previously|earlier|in\s+202[0-5]|in\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+202[0-5]|"
    r"last\s+year|previous\s+round|prior\s+round|seed\s+round\s+in\s+202[0-5]|"
    r"first\s+institutional\s+and\s+angel\s+investment\s+round|earlier\s+in\s+the\s+day)\b",
    re.IGNORECASE,
)

_NON_INVESTOR_PHRASES = frozenset({
    "others", "existing investors", "angel investors", "prominent angels",
    "in the round", "into cards", "the round", "marquee families",
    "a group of", "global vc firm", "previous round", "other returning investors",
    "several angel investors", "two european lenders", "fund", "capital",
    "ventures", "bse", "nse", "sec", "company", "firm",
    "bw disrupt", "entrackr", "inc42", "yourstory", "techcrunch", "dealroom",
    "ibs intelligence", "alleywatch", "fintech global", "reuters", "bloomberg",
    "economic times", "livemint", "moneycontrol", "eu-startups",
})

# Noise tokens to strip
_CLEAN_INVESTOR_RE = re.compile(
    r"\b(?:venture\s+capital|capital|partners|ventures|fund|management|group|investments|holdings)\b",
    re.IGNORECASE,
)


def _clean_investor_name(name: str) -> str:
    """Clean individual investor name."""
    clean = re.sub(r"\([^)]*\)", "", name).strip()
    clean = re.sub(r"^(?:and|from|with|by|the)\s+", "", clean, flags=re.IGNORECASE)
    clean = re.sub(
        r"^(?:alongside(?:\s+new\s+investors?)?\s+|(?:its\s+)?(?:existing|returning|new)\s+(?:investors?|backers?)\s+|"
        r"global\s+vc\s+firm\s+|venture\s+firm\s+|other\s+investors\s+(?:include|included)\s+|(?:its\s+)?existing\s+backer\s+)",
        "",
        clean,
        flags=re.IGNORECASE,
    )
    clean = clean.strip(" ,.;:-")
    return clean


def _is_valid_investor_token(cleaned: str) -> bool:
    low = cleaned.lower()
    if len(cleaned) < 2 or low in _NON_INVESTOR_PHRASES:
        return False
    if "\n" in cleaned or "\r" in cleaned:
        return False
    if low.startswith(("in ", "into ", "from ", "a ", "an ", "two ", "other ", "existing ", "previous ", "with ", "for ", "to ", "founder of ", "co-founder of ", "ceo of ", "an angel ", "marking ")):
        return False
    if any(bad in low for bad in ("declined", "marque", "syndicate", "led the round", "led the investment", "institutional funding", "raised $")):
        return False
    if low == "family":
        return False
    return True


def parse_investor_list(text_block: str) -> list[str]:
    """Split comma- and 'and'-separated list of investor names."""
    if not text_block:
        return []

    # Strip trailing appositive role descriptions like ", founder of Hyperface and Juspay," or ", an angel syndicate,"
    cleaned_block = re.sub(
        r",\s*(?:(?:co-?)?founder|ceo|managing\s+partner|partner|director|an?\s+angel\s+syndicate)\b[^,]*",
        "",
        text_block,
        flags=re.IGNORECASE,
    )

    # Expand "Firstname and Firstname Lastname" (e.g. "Marc and Max Cohodes") -> "Marc Cohodes, Max Cohodes"
    cleaned_block = re.sub(
        r"(?:(?<=^)|(?<=,\s))([A-Z][a-z]{2,})\s+and\s+([A-Z][a-z]{2,})\s+([A-Z][a-z]{2,})(?=$|,)",
        r"\1 \3, \2 \3",
        cleaned_block,
    )

    # Replace ', and ' or ' and ' with comma
    standardized = re.sub(r",?\s+and\s+", ", ", cleaned_block)
    tokens = [t.strip() for t in standardized.split(",") if t.strip()]

    results = []
    for tok in tokens:
        cleaned = _clean_investor_name(tok)
        if _is_valid_investor_token(cleaned):
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

    # 1. Lead investor (pick EARLIEST valid lead match in opening 1500 chars; skip prior-round mentions)
    lead_scope = article_text[:1500]
    lead_candidates: list[tuple[int, list[str], str]] = []
    for pat in _LEAD_PATTERNS:
        for match in pat.finditer(lead_scope):
            context_win = lead_scope[max(0, match.start() - 45) : min(len(lead_scope), match.end() + 45)]
            if _PRIOR_ROUND_CONTEXT.search(context_win):
                continue
            raw_leads = match.group("leads") if "leads" in match.groupdict() else match.group(0).split("-led")[0]
            leads = parse_investor_list(raw_leads)
            if leads:
                lead_candidates.append((match.start(), leads, match.group(0).strip()))

    if lead_candidates:
        lead_candidates.sort(key=lambda item: item[0])
        _, leads, ev_snip = lead_candidates[0]
        lead_investor = leads[0]
        if len(leads) > 1:
            other_investors.extend(leads[1:])
        evidence_parts.append(ev_snip)

    # 2. Participating investors
    for pat in _PARTICIPATING_PATTERNS:
        match = pat.search(lead_scope)
        if match:
            context_win = lead_scope[max(0, match.start() - 45) : min(len(lead_scope), match.end() + 45)]
            if _PRIOR_ROUND_CONTEXT.search(context_win):
                continue
            raw_others = match.group("others")
            others = parse_investor_list(raw_others)
            for inv in others:
                if inv != lead_investor and inv not in other_investors:
                    other_investors.append(inv)
            if others:
                evidence_parts.append(match.group(0).strip())
                break

    # Extended fallback up to 4500 chars for long-form feature articles (e.g. AlleyWatch)
    if lead_investor is None and not other_investors and len(article_text) > 1500:
        ext_scope = article_text[1200:4500]
        for pat in _LEAD_PATTERNS:
            for match in pat.finditer(ext_scope):
                context_win = ext_scope[max(0, match.start() - 45) : min(len(ext_scope), match.end() + 45)]
                if _PRIOR_ROUND_CONTEXT.search(context_win):
                    continue
                raw_leads = match.group("leads") if "leads" in match.groupdict() else match.group(0).split("-led")[0]
                leads = parse_investor_list(raw_leads)
                if leads:
                    lead_investor = leads[0]
                    other_investors.extend(leads[1:])
                    evidence_parts.append(match.group(0).strip())
                    break
            if lead_investor:
                break
        if lead_investor is None:
            for pat in _PARTICIPATING_PATTERNS:
                match = pat.search(ext_scope)
                if match:
                    context_win = ext_scope[max(0, match.start() - 45) : min(len(ext_scope), match.end() + 45)]
                    if _PRIOR_ROUND_CONTEXT.search(context_win):
                        continue
                    others = parse_investor_list(match.group("others"))
                    if others:
                        other_investors.extend(others)
                        evidence_parts.append(match.group(0).strip())
                        break

    # If funding came "from X" without explicit "led by", treat primary investor as lead_investor
    if lead_investor is None and other_investors:
        lead_investor = other_investors.pop(0)

    # Explicit unnamed investor disclosure fallback (never fabricates a firm name)
    if lead_investor is None and re.search(
        r"\b(?:undisclosed\s+(?:family\s+office|investor|backers?)|backers\s+in\s+the\s+round\s+included\s+advisory\s+firms|not\s+disclose\s+(?:the\s+)?(?:investors|backers))\b",
        lead_scope,
        re.IGNORECASE,
    ):
        lead_investor = "Undisclosed"

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
