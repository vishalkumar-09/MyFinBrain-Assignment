"""
classification/relevance_scorer.py
==================================
Calculates holistic startup qualification score combining business category and geography.
"""

from __future__ import annotations

from pydantic import BaseModel
from classification.business_classifier import ClassificationResult, RelevanceStatus
from classification.geography_classifier import GeographyVerificationResult, GeoStatus


class QualificationScore(BaseModel):
    is_qualified: bool
    final_status: str
    relevance_score: float  # 0.0 to 1.0
    confidence_score: float  # 0.0 to 1.0
    summary_reason: str


class RelevanceScorer:
    """
    Computes weighted qualification score.
    A company is only qualified if:
    1. Business category is DIRECT_MATCH or ADJACENT_MATCH.
    2. Geography is VERIFIED in US or India (or flagged NEEDS_REVIEW if ambiguous).
    """

    def score(
        self,
        business: ClassificationResult,
        geography: GeographyVerificationResult,
    ) -> QualificationScore:
        # Check hard disqualifiers
        if business.relevance_status == RelevanceStatus.NOT_RELEVANT:
            return QualificationScore(
                is_qualified=False,
                final_status="NOT_RELEVANT",
                relevance_score=0.0,
                confidence_score=business.classification_confidence,
                summary_reason=business.classification_reasoning,
            )

        if geography.status == GeoStatus.OUT_OF_SCOPE:
            return QualificationScore(
                is_qualified=False,
                final_status="OUT_OF_SCOPE_GEOGRAPHY",
                relevance_score=0.1,
                confidence_score=geography.confidence,
                summary_reason=geography.reasoning,
            )

        # Flag for manual review if either component is inconclusive
        if business.relevance_status == RelevanceStatus.NEEDS_REVIEW or geography.status == GeoStatus.NEEDS_REVIEW:
            return QualificationScore(
                is_qualified=False,
                final_status="NEEDS_REVIEW",
                relevance_score=round((business.relevance_score + 0.4) / 2, 2),
                confidence_score=round((business.classification_confidence + geography.confidence) / 2, 2),
                summary_reason="Ambiguous categorization or unverified headquarters requires manual review.",
            )

        # Qualified: DIRECT_MATCH or ADJACENT_MATCH with VERIFIED geography
        weighted_score = round((business.relevance_score * 0.7) + (geography.confidence * 0.3), 2)
        final_confidence = round((business.classification_confidence * 0.6) + (geography.confidence * 0.4), 2)

        return QualificationScore(
            is_qualified=True,
            final_status=business.relevance_status.value,
            relevance_score=weighted_score,
            confidence_score=final_confidence,
            summary_reason=f"{business.classification_reasoning} {geography.reasoning}",
        )
