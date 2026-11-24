"""
processing/validator.py
=======================
Data integrity validation for extracted startup and funding records.
"""

from __future__ import annotations

from typing import Optional
from datetime import date
from pydantic import BaseModel, Field


class ValidationResult(BaseModel):
    is_valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


def validate_funding_round(
    company_name: str,
    amount: Optional[float],
    currency: Optional[str],
    funding_stage: str,
    announcement_date: Optional[date] = None,
    article_date: Optional[date] = None,
) -> ValidationResult:
    """
    Verify integrity of a funding round record.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not company_name or len(company_name.strip()) < 2:
        errors.append("Company name is missing or too short.")

    if amount is not None and amount <= 0:
        errors.append(f"Funding amount cannot be zero or negative: {amount}")

    if amount is not None and not currency:
        warnings.append("Amount specified without currency code.")

    if funding_stage == "Other":
        warnings.append("Funding stage is uncategorized (Other).")

    if announcement_date and article_date:
        if announcement_date > article_date:
            warnings.append(f"Announcement date ({announcement_date}) is in the future relative to publication date ({article_date}).")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
