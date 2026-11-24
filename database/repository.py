"""
database/repository.py
======================
Repository pattern for database operations: session management, migrations,
entity persistence, and querying.
"""

from __future__ import annotations

import logging
from typing import Optional, List
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session, selectinload

from config.settings import DATABASE_URL
from database.models import Base, Company, FundingRound, Article as DBArticle, Evidence

logger = logging.getLogger(__name__)


class DatabaseRepository:
    """
    Handles SQLite database lifecycle, schema initialization, and transactional operations.
    """

    def __init__(self, db_url: str = DATABASE_URL) -> None:
        self.db_url = db_url
        self.engine = create_engine(
            self.db_url,
            echo=False,
            future=True,
            connect_args={"check_same_thread": False} if "sqlite" in self.db_url else {},
        )
        self.SessionFactory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.init_db()

    def init_db(self) -> None:
        """Create tables if they do not exist."""
        Base.metadata.create_all(self.engine)
        logger.debug("Database initialized at %s", self.db_url)

    def get_session(self) -> Session:
        return self.SessionFactory()

    # ------------------------------------------------------------------
    # Article Operations
    # ------------------------------------------------------------------

    def save_article(
        self,
        url: str,
        canonical_url: str,
        title: str,
        source_name: str,
        published_at=None,
        article_text=None,
        content_hash=None,
        extraction_status="success",
    ) -> DBArticle:
        with self.get_session() as session:
            existing = session.execute(
                select(DBArticle).where(DBArticle.canonical_url == canonical_url)
            ).scalar_one_or_none()
            if existing:
                if published_at and not existing.published_at:
                    existing.published_at = published_at
                if article_text and not existing.article_text:
                    existing.article_text = article_text
                    existing.content_hash = content_hash
                    existing.extraction_status = extraction_status
                session.commit()
                return existing

            art = DBArticle(
                url=url,
                canonical_url=canonical_url,
                title=title,
                source_name=source_name,
                published_at=published_at,
                article_text=article_text,
                content_hash=content_hash,
                extraction_status=extraction_status,
            )
            session.add(art)
            session.commit()
            session.refresh(art)
            return art

    # ------------------------------------------------------------------
    # Company Operations
    # ------------------------------------------------------------------

    def get_all_companies(self) -> List[Company]:
        with self.get_session() as session:
            stmt = select(Company).order_by(Company.canonical_name)
            return list(session.execute(stmt).scalars().all())

    def get_company_by_id(self, company_id: int) -> Optional[Company]:
        with self.get_session() as session:
            return session.get(Company, company_id)

    def save_company(self, company: Company) -> Company:
        with self.get_session() as session:
            session.add(company)
            session.commit()
            session.refresh(company)
            return company

    # ------------------------------------------------------------------
    # Funding Round Operations
    # ------------------------------------------------------------------

    def get_funding_rounds_for_company(self, company_id: int) -> List[FundingRound]:
        with self.get_session() as session:
            stmt = (
                select(FundingRound)
                .options(selectinload(FundingRound.evidence_records).selectinload(Evidence.article))
                .where(FundingRound.company_id == company_id)
                .order_by(FundingRound.created_at)
            )
            return list(session.execute(stmt).scalars().all())

    def save_funding_round(self, funding_round: FundingRound) -> FundingRound:
        with self.get_session() as session:
            session.add(funding_round)
            session.commit()
            session.refresh(funding_round)
            return funding_round

    # ------------------------------------------------------------------
    # Evidence Operations
    # ------------------------------------------------------------------

    def save_evidence(
        self,
        field_name: str,
        evidence_text: str,
        article_id: Optional[int] = None,
        company_id: Optional[int] = None,
        funding_round_id: Optional[int] = None,
        confidence: float = 1.0,
    ) -> Evidence:
        with self.get_session() as session:
            ev = Evidence(
                field_name=field_name,
                evidence_text=evidence_text,
                article_id=article_id,
                company_id=company_id,
                funding_round_id=funding_round_id,
                confidence=confidence,
            )
            session.add(ev)
            session.commit()
            session.refresh(ev)
            return ev
