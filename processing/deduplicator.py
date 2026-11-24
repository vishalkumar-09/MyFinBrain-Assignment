"""
processing/deduplicator.py
==========================
Funding round deduplication and evidence aggregation engine.

Rules:
1. Multiple articles reporting the same round map to ONE funding round with
   multiple evidence records.
2. One company raising multiple different rounds (e.g. Seed in 2024, Series A in 2025)
   produces separate FundingRound records.
3. Matches on:
   - Same company ID
   - Same funding stage (or stage compatibility)
   - Date proximity (within 45 days) OR exact amount match
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Optional, List
from database.models import FundingRound

logger = logging.getLogger(__name__)


class FundingRoundDeduplicator:
    """
    Determines whether an extracted funding event matches an existing round or is a new round.
    """

    def find_matching_round(
        self,
        company_id: int,
        stage: str,
        amount: Optional[float],
        currency: Optional[str],
        announcement_date: Optional[date],
        existing_rounds: List[FundingRound],
    ) -> tuple[Optional[FundingRound], str]:
        """
        Check existing rounds for the company to detect duplicate coverage.
        Returns (matched_round, match_reason).
        """
        company_rounds = [r for r in existing_rounds if r.company_id == company_id]
        if not company_rounds:
            return None, "New company round"

        for r in company_rounds:
            # 1. Check stage compatibility
            same_stage = (r.funding_stage.lower() == stage.lower()) or (
                r.funding_stage in ("Other", "Undisclosed") or stage in ("Other", "Undisclosed")
            )

            # 2. Check amount match
            same_amount = False
            if amount is not None and r.amount is not None:
                if currency and r.currency and currency == r.currency:
                    # Allow within 2% margin for rounding variations
                    if abs(amount - r.amount) / max(amount, r.amount) < 0.02:
                        same_amount = True
            elif amount is None and r.amount is None:
                same_amount = True  # both undisclosed

            # 3. Check date proximity
            close_date = False
            if announcement_date and r.announcement_date:
                days_diff = abs((announcement_date - r.announcement_date).days)
                if days_diff <= 45:
                    close_date = True

            # Matching criteria:
            # Same stage AND (same amount OR close date)
            if same_stage and (same_amount or close_date):
                return r, f"Matched round on stage={r.funding_stage} (amount_match={same_amount}, date_match={close_date})"

        return None, "Distinct funding round"
