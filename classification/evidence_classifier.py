"""
classification/evidence_classifier.py
=====================================
Compiles and validates auditable evidence trails for classification & verification decisions.
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class EvidenceRecord(BaseModel):
    field_name: str
    evidence_text: str
    confidence: float = 1.0
    source_context: str = ""


class EvidenceTracker:
    """
    Assembles evidence records across company name, funding amount, category, and geography.
    """

    def compile_evidence(
        self,
        company_evidence: Optional[str],
        amount_evidence: Optional[str],
        category_evidence: list[str],
        geo_evidence: Optional[str],
    ) -> list[EvidenceRecord]:
        records: list[EvidenceRecord] = []

        if company_evidence:
            records.append(
                EvidenceRecord(
                    field_name="company_name",
                    evidence_text=company_evidence,
                    confidence=0.95,
                    source_context="Headline / Lead Sentence",
                )
            )

        if amount_evidence:
            records.append(
                EvidenceRecord(
                    field_name="funding_amount",
                    evidence_text=amount_evidence,
                    confidence=0.95,
                    source_context="Funding Announcement Paragraph",
                )
            )

        for cat_hit in category_evidence:
            records.append(
                EvidenceRecord(
                    field_name="business_category",
                    evidence_text=cat_hit,
                    confidence=0.90,
                    source_context="Product / Service Description",
                )
            )

        if geo_evidence:
            records.append(
                EvidenceRecord(
                    field_name="headquarters_location",
                    evidence_text=geo_evidence,
                    confidence=0.90,
                    source_context="Headquarters Attribution",
                )
            )

        return records
