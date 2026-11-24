"""
discovery/query_builder.py
==========================
Generates structured search queries for article discovery.

Design goals:
- Queries are built from configuration, not hardcoded in adapters.
- Different source types get query formats tailored to their interface.
- Country-specific targeting improves precision.
- Queries are deduped and ranked by specificity.
- Adding a new keyword in config/keywords.py auto-propagates here.
"""

from __future__ import annotations

import hashlib
import itertools
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from config.keywords import (
    BUSINESS_KEYWORDS,
    FUNDING_KEYWORDS,
    GEO_QUALIFIERS,
)
from config.settings import TARGET_COUNTRIES

logger = logging.getLogger(__name__)


class QueryType(str, Enum):
    """The interface format a query is intended for."""
    RSS_SEARCH = "rss_search"      # Google News / similar RSS search endpoints
    SITE_SEARCH = "site_search"    # Site-specific search boxes
    API_SEARCH = "api_search"      # Structured API filters
    KEYWORD = "keyword"            # Plain keyword for general use


@dataclass(frozen=True)
class SearchQuery:
    """
    Immutable search query object.

    Carries both the query string and the metadata needed to track
    which query produced which article.
    """
    text: str
    query_type: QueryType
    business_category: Optional[str] = None
    funding_keyword: Optional[str] = None
    geo_qualifier: Optional[str] = None
    country: Optional[str] = None
    priority: int = 5  # 1 (highest) → 10 (lowest)

    @property
    def query_id(self) -> str:
        """Stable hash id for this query (used as a cache key)."""
        return hashlib.md5(
            f"{self.query_type}:{self.text}".encode()
        ).hexdigest()[:12]

    def __str__(self) -> str:
        return self.text


class QueryBuilder:
    """
    Generates deduplicated, prioritised search queries.

    Strategies:
    1. High-priority: exact business domain + explicit funding event  ("wealthtech Series A")
    2. Medium-priority: business domain + country qualifier           ("private equity India funding")
    3. Lower-priority: broad domain-only queries                      ("family office technology")
    """

    # Maximum queries returned by default (None = all queries)
    DEFAULT_MAX: Optional[int] = None

    def __init__(
        self,
        business_keywords: list[str] = BUSINESS_KEYWORDS,
        funding_keywords: list[str] = FUNDING_KEYWORDS,
        geo_qualifiers: dict[str, list[str]] = GEO_QUALIFIERS,
        target_countries: list[str] = TARGET_COUNTRIES,
    ) -> None:
        self._biz = business_keywords
        self._fund = funding_keywords
        self._geo = geo_qualifiers
        self._countries = target_countries
        self._seen: set[str] = set()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build_all(self, max_queries: Optional[int] = DEFAULT_MAX) -> list[SearchQuery]:
        """
        Return the full prioritised query list, capped at ``max_queries`` if provided.
        """
        queries: list[SearchQuery] = []
        queries.extend(self._tier1_specific())
        queries.extend(self._tier2_geo_targeted())
        queries.extend(self._tier3_broad())
        # Reset seen set for the next call
        self._seen.clear()
        if max_queries is not None:
            return queries[:max_queries]
        return queries

    def build_for_rss(self, max_queries: int = 100) -> list[SearchQuery]:
        """Return queries suitable for Google News / RSS search."""
        all_q = self.build_all(max_queries * 3)
        rss_q = [q for q in all_q if q.query_type == QueryType.RSS_SEARCH]
        return rss_q[:max_queries]

    def build_for_country(
        self,
        country: str,
        max_queries: int = 100,
    ) -> list[SearchQuery]:
        """Return queries scoped to a single target country."""
        all_q = self.build_all(max_queries * 3)
        filtered = [q for q in all_q if q.country == country or q.country is None]
        return filtered[:max_queries]

    def build_stage_specific(
        self,
        stage: str,
        max_queries: int = 50,
    ) -> list[SearchQuery]:
        """Return queries focusing on one funding stage (e.g. 'Series A')."""
        queries: list[SearchQuery] = []
        for biz in self._biz[:10]:
            q = self._make(
                text=f"{biz} {stage}",
                query_type=QueryType.RSS_SEARCH,
                business_category=biz,
                funding_keyword=stage,
                priority=2,
            )
            if q:
                queries.append(q)
        return queries[:max_queries]

    # ------------------------------------------------------------------
    # Internal tiers
    # ------------------------------------------------------------------

    def _tier1_specific(self) -> list[SearchQuery]:
        """
        Tier 1 (priority 2): business keyword + funding keyword pairs.
        These are the most precise queries and produce the highest-quality hits.
        """
        queries: list[SearchQuery] = []
        for biz, fund in itertools.product(self._biz, self._fund):
            q = self._make(
                text=f"{biz} {fund}",
                query_type=QueryType.RSS_SEARCH,
                business_category=biz,
                funding_keyword=fund,
                priority=2,
            )
            if q:
                queries.append(q)
        return queries

    def _tier2_geo_targeted(self) -> list[SearchQuery]:
        """
        Tier 2 (priority 3): business keyword + geo qualifier + "funding".
        Improves recall for India- and US-specific coverage.
        """
        queries: list[SearchQuery] = []
        for country, qualifiers in self._geo.items():
            for qual, biz in itertools.product(qualifiers, self._biz[:8]):
                # e.g. "wealth management Indian startup funding"
                q = self._make(
                    text=f"{biz} {qual} funding",
                    query_type=QueryType.RSS_SEARCH,
                    business_category=biz,
                    geo_qualifier=qual,
                    country=country,
                    priority=3,
                )
                if q:
                    queries.append(q)
        return queries

    def _tier3_broad(self) -> list[SearchQuery]:
        """
        Tier 3 (priority 5): domain-only queries for broad discovery.
        Highest recall but lowest precision; useful for finding edge cases.
        """
        queries: list[SearchQuery] = []
        for biz in self._biz:
            q = self._make(
                text=f"{biz} startup funding",
                query_type=QueryType.RSS_SEARCH,
                business_category=biz,
                priority=5,
            )
            if q:
                queries.append(q)
        # Also add pure funding-stage queries
        priority_stages = [
            "Series A startup", "Series B startup", "seed round startup",
            "pre-seed startup", "angel investment startup",
        ]
        for stage_q in priority_stages:
            q = self._make(
                text=stage_q,
                query_type=QueryType.RSS_SEARCH,
                priority=5,
            )
            if q:
                queries.append(q)
        return queries

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _make(
        self,
        text: str,
        query_type: QueryType,
        business_category: Optional[str] = None,
        funding_keyword: Optional[str] = None,
        geo_qualifier: Optional[str] = None,
        country: Optional[str] = None,
        priority: int = 5,
    ) -> Optional[SearchQuery]:
        """Create a SearchQuery if ``text`` has not been seen before."""
        norm = text.strip().lower()
        if norm in self._seen:
            return None
        self._seen.add(norm)
        return SearchQuery(
            text=text.strip(),
            query_type=query_type,
            business_category=business_category,
            funding_keyword=funding_keyword,
            geo_qualifier=geo_qualifier,
            country=country,
            priority=priority,
        )

    def summary(self) -> str:
        queries = self.build_all()
        tier_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for q in queries:
            tier_counts[min(q.priority, 5)] = tier_counts.get(min(q.priority, 5), 0) + 1
        lines = [f"QueryBuilder summary: {len(queries)} total queries"]
        for p, count in sorted(tier_counts.items()):
            lines.append(f"  Priority {p}: {count} queries")
        return "\n".join(lines)
