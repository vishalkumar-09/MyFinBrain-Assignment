"""
sources/verification/company_website.py
========================================
Company website and multi-source corroboration verifier.

Used during classification and geography verification when a primary funding
article omits explicit headquarters location details. Strictly avoids guessing:
only assigns United States or India (or out-of-scope country) when an actual
live web page or corroborating news/PR report explicitly states the city/HQ.
"""
from __future__ import annotations

import logging
import re
import urllib.parse
from typing import Iterator, Optional

import feedparser

from classification.geography_classifier import (
    GeographyClassifier,
    GeographyVerificationResult,
    GeoStatus,
)
from extraction.article_parser import ArticleParser
from extraction.company_extractor import extract_location
from sources import registry
from sources.base import Article, BaseSource
from sources.bing_news import extract_direct_publisher_url

logger = logging.getLogger(__name__)

_SKIP_VERIFY_DOMAINS = frozenset({
    "wsj.com",
    "ft.com",
    "barrons.com",
    "bloomberg.com",
    "citywire.com",
    "msn.com",
})

# Strict address footer / state pattern on official company websites (e.g. "New York, NY", "Miami, FL")
_WEBSITE_US_ADDR_RE = re.compile(
    r"\b(?P<city>San Francisco|New York|Austin|Boston|Seattle|Chicago|Los Angeles|Miami|"
    r"Indianapolis|Denver|Atlanta|Dallas|Houston|Washington|Jersey City|Reno|Charlotte|Stamford|Palo Alto),"
    r"\s*(?:CA|NY|TX|MA|WA|IL|FL|IN|CO|GA|DC|D\.C\.|NJ|NV|NC|CT)\b",
)

_WEBSITE_INDIA_ADDR_RE = re.compile(
    r"\b(?P<city>Bengaluru|Bangalore|Mumbai|New Delhi|Delhi|Gurugram|Gurgaon|Noida|Pune|Hyderabad|Chennai),"
    r"\s*(?:Karnataka|Maharashtra|Delhi|Haryana|Uttar Pradesh|Telangana|Tamil Nadu|India)\b",
    re.IGNORECASE,
)


_SECTOR_OVERLAP_RE = re.compile(
    r"\b(?:wealth|wealthtech|invest(?:ment|ing|or|ors)|capital\s+markets|private\s+(?:equity|credit|markets|funds)|"
    r"alternative\s+(?:investments?|assets)|alternatives|portfolio|advisor|adviser|ria|hedge\s+fund|"
    r"tokeni[sz]ed|corporate\s+access|asset\s+management|mutual\s+fund|brokerage|fixed[\s-]income)\b",
    re.IGNORECASE,
)


def verify_company_hq_live(
    company_name: str,
    geo_classifier: GeographyClassifier,
    article_parser: Optional[ArticleParser] = None,
    website: Optional[str] = None,
    lead_investor: Optional[str] = None,
    sector_hint: Optional[str] = None,
    max_corroborations: int = 5,
) -> tuple[Optional[GeographyVerificationResult], Optional[str]]:
    """
    Attempt to verify headquarters country & city from live external sources
    (official company website first, then corroborating Bing News coverage).

    Returns ``(verified_geo_result, evidence_url)`` or ``(None, None)``.
    Never guesses: only returns VERIFIED or OUT_OF_SCOPE if explicitly evidenced.
    """
    parser = article_parser or ArticleParser(timeout=10)
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
    }

    # 1. Check extracted official company website (homepage + /about or /contact)
    if website:
        for path in ("", "/about", "/contact"):
            try:
                target = website.rstrip("/") + path
                resp = parser.session.get(target, headers=headers, timeout=8)
                if resp.status_code != 200:
                    continue
                parsed_art = parser.parse_html(resp.text, target)
                body = parsed_art.full_text or ""
                # Check strict address regex and standard HQ patterns
                m_us = _WEBSITE_US_ADDR_RE.search(resp.text)
                if m_us:
                    geo = geo_classifier.verify(
                        company_name=company_name,
                        extracted_city=m_us.group("city"),
                        extracted_country="United States",
                        article_text=body[:3000],
                    )
                    if geo.status != GeoStatus.NEEDS_REVIEW:
                        return geo, target
                m_in = _WEBSITE_INDIA_ADDR_RE.search(resp.text)
                if m_in:
                    geo = geo_classifier.verify(
                        company_name=company_name,
                        extracted_city=m_in.group("city"),
                        extracted_country="India",
                        article_text=body[:3000],
                    )
                    if geo.status != GeoStatus.NEEDS_REVIEW:
                        return geo, target
                geo = geo_classifier.verify(company_name=company_name, article_text=body[:4000])
                if geo.status in (GeoStatus.VERIFIED, GeoStatus.OUT_OF_SCOPE):
                    return geo, target
            except Exception:
                continue

    # 2. Check corroborating press / news articles via Bing News RSS (never use boolean OR in Bing RSS)
    queries: list[str] = []
    lead_token = lead_investor.split(",")[0].strip() if lead_investor else ""
    if len(lead_token) >= 3:
        queries.append(f'"{company_name}" "{lead_token}"')
    if sector_hint:
        queries.append(f'"{company_name}" {sector_hint}')
    queries.append(f'"{company_name}" citybiz')
    if len(company_name.split()) == 1:
        queries.append(f'"{company_name}" wealthtech')
        queries.append(f'"{company_name}" investment')
    queries.append(f'"{company_name}"')
    queries.append(f'"{company_name}" India')

    short_key = company_name.split()[0].lower()
    is_single_word = len(company_name.split()) == 1
    seen_urls: set[str] = set()
    checked = 0
    best_country_only: Optional[tuple[GeographyVerificationResult, str]] = None

    def _matches_target_company(txt: str) -> bool:
        low = txt.lower()
        if company_name.lower() not in low and (len(short_key) < 4 or short_key not in low):
            return False
        # Guard single-word generic names (Aqua, Axle, Nevis, Fission) against cross-industry collisions
        if is_single_word:
            has_lead = len(lead_token) >= 3 and lead_token.lower() in low
            has_sector = bool(_SECTOR_OVERLAP_RE.search(txt))
            if not (has_lead or has_sector):
                return False
        return True

    for query in queries:
        if checked >= 8:
            break
        query_fetches = 0
        try:
            r = parser.session.get(
                "https://www.bing.com/news/search",
                params={"q": query, "format": "rss"},
                headers=headers,
                timeout=10,
            )
            if r.status_code != 200:
                continue
            fp = feedparser.parse(r.text)
            for entry in fp.entries:
                if checked >= 8 or query_fetches >= 2:
                    break
                title = (getattr(entry, "title", "") or "").strip()
                desc = (getattr(entry, "description", "") or "").strip()
                raw_link = getattr(entry, "link", "") or ""
                direct_url = extract_direct_publisher_url(raw_link)
                if not direct_url or direct_url in seen_urls:
                    continue
                seen_urls.add(direct_url)
                host = urllib.parse.urlparse(direct_url).netloc.lower()
                if any(host == d or host.endswith(f".{d}") for d in _SKIP_VERIFY_DOMAINS):
                    continue
                # Ensure the corroborating story is actually about this company
                snip_text = f"{title}\n{desc}"
                if not _matches_target_company(snip_text):
                    continue

                # Check snippet description first (often contains PR dateline like "CHICAGO, Oct. 14")
                city, country = extract_location(snip_text, company_name=company_name)
                geo = geo_classifier.verify(
                    company_name=company_name,
                    extracted_city=city,
                    extracted_country=country,
                    article_text=snip_text,
                )
                if geo.status == GeoStatus.OUT_OF_SCOPE or (geo.status == GeoStatus.VERIFIED and geo.headquarters_city):
                    return geo, direct_url
                if geo.status == GeoStatus.VERIFIED and best_country_only is None:
                    best_country_only = (geo, direct_url)

                # Otherwise fetch full corroborating article HTML (cap per query so later fallback queries still run)
                checked += 1
                query_fetches += 1
                try:
                    art_resp = parser.session.get(direct_url, headers=headers, timeout=10)
                    if art_resp.status_code == 200:
                        parsed_art = parser.parse_html(art_resp.text, direct_url)
                        body = parsed_art.full_text or ""
                        if _matches_target_company(body):
                            city, country = extract_location(body[:6000], company_name=company_name)
                            geo = geo_classifier.verify(
                                company_name=company_name,
                                extracted_city=city,
                                extracted_country=country,
                                article_text=body[:6000],
                            )
                            if geo.status == GeoStatus.OUT_OF_SCOPE or (geo.status == GeoStatus.VERIFIED and geo.headquarters_city):
                                return geo, direct_url
                            if geo.status == GeoStatus.VERIFIED and best_country_only is None:
                                best_country_only = (geo, direct_url)
                except Exception:
                    continue
        except Exception as exc:
            logger.debug("Corroborating HQ lookup failed for %s (%s): %s", company_name, query, exc)

    if best_country_only is not None:
        return best_country_only
    return None, None


@registry.register
class CompanyWebsiteSource(BaseSource):
    """
    Verification adapter: not used for discovery.
    The live verification helper lives in ``verify_company_hq_live``.
    """

    SOURCE_ID = "company_website"
    SOURCE_NAME = "Company Website"

    def discover(self) -> Iterator[Article]:
        self._logger.debug("CompanyWebsiteSource is a verification-only adapter.")
        return
        yield
