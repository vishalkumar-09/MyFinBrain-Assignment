"""
database/models.py
==================
SQLAlchemy 2.0 ORM models for companies, funding rounds, articles, and evidence.

Entities:
- Companies: Canonical entity records for deduplicated startups
- FundingRounds: Individual financing events for a company
- Articles: Discovered news and press releases
- Evidence: Field-level evidence mapping back to source articles
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional, List
from sqlalchemy import (
    String,
    Float,
    Integer,
    DateTime,
    Date,
    ForeignKey,
    Text,
    JSON,
    Index,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    canonical_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    website_domain: Mapped[Optional[str]] = mapped_column(String(255), index=True, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    headquarters_country: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    headquarters_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    operating_countries: Mapped[Optional[list[str]]] = mapped_column(JSON, default=list)
    primary_category: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    secondary_categories: Mapped[Optional[list[str]]] = mapped_column(JSON, default=list)
    relevance_status: Mapped[str] = mapped_column(String(50), default="NOT_RELEVANT", index=True)
    classification_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    funding_rounds: Mapped[List[FundingRound]] = relationship("FundingRound", back_populates="company", cascade="all, delete-orphan")
    evidence_records: Mapped[List[Evidence]] = relationship("Evidence", back_populates="company", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Company id={self.id} name={self.canonical_name!r} status={self.relevance_status!r}>"


class FundingRound(Base):
    __tablename__ = "funding_rounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=False)
    original_amount_text: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    normalized_amount_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    funding_stage: Mapped[str] = mapped_column(String(100), default="Other", index=True)
    announcement_date: Mapped[Optional[date]] = mapped_column(Date, index=True, nullable=True)
    lead_investor: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    investors: Mapped[Optional[list[str]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    company: Mapped[Company] = relationship("Company", back_populates="funding_rounds")
    evidence_records: Mapped[List[Evidence]] = relationship("Evidence", back_populates="funding_round", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<FundingRound id={self.id} company_id={self.company_id} stage={self.funding_stage!r} amount={self.amount}>"


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_url: Mapped[str] = mapped_column(String(500), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_name: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    article_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True, nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    extraction_status: Mapped[str] = mapped_column(String(50), default="pending")

    # Relationships
    evidence_records: Mapped[List[Evidence]] = relationship("Evidence", back_populates="article")

    def __repr__(self) -> str:
        return f"<Article id={self.id} canonical_url={self.canonical_url!r}>"


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    article_id: Mapped[Optional[int]] = mapped_column(ForeignKey("articles.id", ondelete="SET NULL"), index=True, nullable=True)
    company_id: Mapped[Optional[int]] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), index=True, nullable=True)
    funding_round_id: Mapped[Optional[int]] = mapped_column(ForeignKey("funding_rounds.id", ondelete="CASCADE"), index=True, nullable=True)
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    article: Mapped[Optional[Article]] = relationship("Article", back_populates="evidence_records")
    company: Mapped[Optional[Company]] = relationship("Company", back_populates="evidence_records")
    funding_round: Mapped[Optional[FundingRound]] = relationship("FundingRound", back_populates="evidence_records")

    def __repr__(self) -> str:
        return f"<Evidence id={self.id} field={self.field_name!r}>"
