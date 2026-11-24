"""
sources/base.py
===============
Abstract BaseSource and standardised data models for all source adapters.

Design principles:
- Every adapter returns ``Article`` objects.
- The pipeline never needs to know which concrete adapter it is talking to.
- Adding a new source means adding a new module; zero changes to the core pipeline.
"""

from __future__ import annotations

import hashlib
import logging
import time
import urllib.parse
from abc import ABC, abstractmethod
from datetime import date, datetime, timezone
from enum import Enum
from typing import Generator, Iterator, Optional
from urllib.parse import urlparse, urlunparse, urlencode, parse_qs

import requests
from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

logger = logging.getLogger(__name__)


# ===========================================================================
# Data models
# ===========================================================================

class ExtractionStatus(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class Article(BaseModel):
    """
    Canonical representation of a discovered article / press release.
    Returned by every source adapter.
    """

    # Identity
    url: str
    canonical_url: Optional[str] = None
    title: str
    source_id: str
    source_name: str

    # Content
    summary: Optional[str] = None          # From RSS / metadata
    full_text: Optional[str] = None        # Filled in extraction phase
    author: Optional[str] = None

    # Dates
    published_at: Optional[datetime] = None
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Discovery provenance
    discovery_query: Optional[str] = None  # Search query that found this
    feed_url: Optional[str] = None         # RSS feed or API endpoint

    # Processing state
    extraction_status: ExtractionStatus = ExtractionStatus.PENDING
    content_hash: Optional[str] = None

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def set_canonical_url(self) -> "Article":
        if self.canonical_url is None:
            self.canonical_url = canonicalize_url(self.url)
        return self

    @model_validator(mode="after")
    def compute_content_hash(self) -> "Article":
        if self.content_hash is None and self.full_text:
            self.content_hash = hashlib.sha256(
                self.full_text.encode("utf-8", errors="replace")
            ).hexdigest()
        return self

    def is_within_date_range(
        self, start: date, end: date
    ) -> bool:
        """Return True if the article's publication date falls within [start, end]."""
        if self.published_at is None:
            return True  # Cannot filter; keep for later review
        pub_date = self.published_at.date()
        return start <= pub_date <= end


class SourceHealth(BaseModel):
    """Runtime statistics for one source adapter execution."""

    source_id: str
    articles_found: int = 0
    articles_failed: int = 0
    errors: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    success: bool = True

    def record_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.success = False

    def finish(self) -> None:
        self.finished_at = datetime.now(timezone.utc)


# ===========================================================================
# URL utilities
# ===========================================================================

# Query parameters that are purely tracking / session noise
_STRIP_PARAMS = frozenset({
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "msclkid", "ref", "source", "mc_cid", "mc_eid",
    "WT.mc_id", "_ga", "si",
})


def canonicalize_url(url: str) -> str:
    """
    Normalise a URL for deduplication:
    1. Lowercase scheme and host.
    2. Remove tracking query parameters.
    3. Remove trailing slash from path (except root).
    4. Drop fragment.
    """
    try:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/") or "/"
        # Strip tracking params
        qs = parse_qs(parsed.query, keep_blank_values=False)
        clean_qs = {k: v for k, v in qs.items() if k not in _STRIP_PARAMS}
        query = urlencode(
            {k: v[0] for k, v in sorted(clean_qs.items())},
            quote_via=urllib.parse.quote,
        )
        return urlunparse((scheme, netloc, path, "", query, ""))
    except Exception:
        return url


# ===========================================================================
# HTTP session helper
# ===========================================================================

def build_session(
    user_agent: str,
    timeout: int = 30,
) -> requests.Session:
    """Return a requests Session pre-configured with headers and retry."""
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
    )
    retry_strategy = Retry(
        total=3,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


# ===========================================================================
# Abstract base
# ===========================================================================

class BaseSource(ABC):
    """
    Abstract base class for all data source adapters.

    Subclasses MUST set ``SOURCE_ID`` and implement ``discover()``.
    They register themselves via ``sources.registry.register``.
    """

    SOURCE_ID: str = ""         # Unique identifier matching source_config.py
    SOURCE_NAME: str = ""       # Human-readable name

    def __init__(
        self,
        start_date: date,
        end_date: date,
        user_agent: str = "StartupFundingIntelligence/1.0",
        request_delay: float = 1.0,
        timeout: int = 30,
    ) -> None:
        self.start_date = start_date
        self.end_date = end_date
        self.user_agent = user_agent
        self.request_delay = request_delay
        self.timeout = timeout
        self._session: Optional[requests.Session] = None
        self.health = SourceHealth(source_id=self.SOURCE_ID)
        self._logger = logging.getLogger(
            f"{__name__}.{self.__class__.__name__}"
        )

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = build_session(self.user_agent, self.timeout)
        return self._session

    def _throttle(self) -> None:
        """Sleep for the configured request delay."""
        if self.request_delay > 0:
            time.sleep(self.request_delay)

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _get(
        self,
        url: str,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        retries: int = 3,
    ) -> Optional[requests.Response]:
        """
        Perform a GET request with exponential backoff on transient errors.
        Returns None on unrecoverable failure (logs the error).
        """
        for attempt in range(1, retries + 1):
            try:
                self._throttle()
                resp = self.session.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                )
                if resp.status_code == 429:
                    wait = min(2 ** attempt * 2, 6)
                    self._logger.warning(
                        "HTTP 429 from %s – waiting %ds (attempt %d/%d)",
                        url, wait, attempt, retries,
                    )
                    time.sleep(wait)
                    continue
                if resp.status_code >= 400:
                    self._logger.warning(
                        "HTTP %d from %s", resp.status_code, url
                    )
                    return None
                return resp
            except requests.RequestException as exc:
                wait = 2 ** attempt
                self._logger.warning(
                    "Request error (attempt %d/%d): %s – %s",
                    attempt, retries, url, exc,
                )
                if attempt < retries:
                    time.sleep(wait)
        self._logger.error("All %d attempts failed for %s", retries, url)
        self.health.record_error(f"Request failed after {retries} retries: {url}")
        return None

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def discover(self) -> Iterator[Article]:
        """
        Yield ``Article`` objects discovered from this source.
        Must handle its own errors internally and never raise.
        """
        ...

    # ------------------------------------------------------------------
    # Optional hooks
    # ------------------------------------------------------------------

    def check_access(self) -> tuple[bool, str]:
        """
        Quickly verify that the source is reachable and accessible.
        Returns (is_accessible, message).
        Default implementation returns (True, "not checked").
        Override for sources requiring authentication.
        """
        return True, "not checked"

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def run(self) -> tuple[list[Article], SourceHealth]:
        """
        Execute discovery, collect results, and return them with health stats.
        Exceptions are caught so one source failure never stops the pipeline.
        """
        self.health = SourceHealth(source_id=self.SOURCE_ID)
        articles: list[Article] = []
        try:
            for article in self.discover():
                if article.is_within_date_range(self.start_date, self.end_date):
                    articles.append(article)
                    self.health.articles_found += 1
        except Exception as exc:  # noqa: BLE001
            msg = f"Unhandled error in {self.SOURCE_ID}: {exc}"
            self._logger.exception(msg)
            self.health.record_error(msg)
            self.health.success = False
        finally:
            self.health.finish()
        return articles, self.health

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} source_id={self.SOURCE_ID!r}>"
