"""
processing/entity_resolution.py
===============================
Entity resolution and company deduplication engine.

Resolution Strategy:
1. Exact Website Domain: If official websites share domain (e.g. 'wealthai.io'),
   they are 100% the same company.
2. Exact Normalized Name: 'WealthAI, Inc.' and 'WealthAI LLC' normalize to 'wealthai'
   and match with 100% confidence.
3. Fuzzy Name Matching: RapidFuzz token_sort_ratio >= 90% combined with
   compatible location or category match.
4. Ambiguity Guard: Intermediate scores (75%-89%) without strong domain or location
   overlap are kept separate to prevent false merges.
"""

from __future__ import annotations

import logging
from typing import Optional, List
from rapidfuzz import fuzz

from database.models import Company
from processing.normalizer import normalize_company_name, extract_website_domain

logger = logging.getLogger(__name__)


class CompanyEntityResolver:
    """
    Resolves extracted startup mentions against existing canonical Company records.
    """

    def __init__(self, fuzzy_threshold: float = 90.0) -> None:
        self.fuzzy_threshold = fuzzy_threshold

    def resolve(
        self,
        name: str,
        website: Optional[str] = None,
        country: Optional[str] = None,
        city: Optional[str] = None,
        existing_companies: Optional[List[Company]] = None,
    ) -> tuple[Optional[Company], float, str]:
        """
        Attempt to resolve a company candidate against existing companies.
        Returns (matched_company, confidence, match_reason).
        If no match is found, returns (None, 0.0, 'No match').
        """
        if not existing_companies:
            return None, 0.0, "No existing companies"

        cand_norm_name = normalize_company_name(name)
        cand_domain = extract_website_domain(website)

        # 1. Exact Domain Match (Highest Confidence)
        if cand_domain:
            for comp in existing_companies:
                if comp.website_domain and comp.website_domain == cand_domain:
                    return comp, 1.0, f"Exact domain match: {cand_domain}"

        # 2. Exact Normalized Name Match
        for comp in existing_companies:
            if comp.normalized_name == cand_norm_name:
                # Check country compatibility
                if country and comp.headquarters_country and country != comp.headquarters_country:
                    continue  # Different countries with same generic name
                return comp, 0.98, f"Exact normalized name match: {cand_norm_name}"

        # 3. Fuzzy Name Match with Contextual Compatibility
        best_match = None
        best_score = 0.0

        for comp in existing_companies:
            score = fuzz.token_sort_ratio(cand_norm_name, comp.normalized_name)
            if score >= self.fuzzy_threshold and score > best_score:
                # Require country compatibility for fuzzy matches
                if country and comp.headquarters_country and country != comp.headquarters_country:
                    continue
                best_match = comp
                best_score = score

        if best_match and best_score >= self.fuzzy_threshold:
            conf = round(best_score / 100.0, 2)
            return best_match, conf, f"Fuzzy name match ({best_score:.1f}%): {cand_norm_name} ~ {best_match.normalized_name}"

        return None, 0.0, "No matching entity found"
