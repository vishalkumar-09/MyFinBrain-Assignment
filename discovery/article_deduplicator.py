"""
discovery/article_deduplicator.py
==================================
Multi-stage article deduplication.

Stage 1 – URL deduplication
    Canonicalize URLs and reject any article whose canonical URL has been
    seen before.  This catches the most common case: the same article
    shared with different tracking parameters.

Stage 2 – Content-hash deduplication
    If two articles have the same full_text SHA-256 hash they are the same
    article, regardless of URL.  Applied after content extraction.

Stage 3 – Title-similarity deduplication (fuzzy)
    Use RapidFuzz token_sort_ratio to detect near-duplicate titles
    (threshold configurable; default 92).  Applied conservatively to avoid
    merging legitimately different articles about the same company.

The deduplicator is stateful – it accumulates seen IDs in memory and
optionally persists them to a JSON checkpoint file so the pipeline can
resume without reprocessing previously seen articles.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from rapidfuzz import fuzz

from sources.base import Article, canonicalize_url

logger = logging.getLogger(__name__)


@dataclass
class DeduplicationStats:
    total_seen: int = 0
    url_duplicates: int = 0
    hash_duplicates: int = 0
    title_duplicates: int = 0
    accepted: int = 0

    @property
    def total_rejected(self) -> int:
        return self.url_duplicates + self.hash_duplicates + self.title_duplicates

    def __str__(self) -> str:
        return (
            f"Dedup stats: seen={self.total_seen}, "
            f"accepted={self.accepted}, "
            f"rejected={self.total_rejected} "
            f"(url={self.url_duplicates}, "
            f"hash={self.hash_duplicates}, "
            f"title={self.title_duplicates})"
        )


class ArticleDeduplicator:
    """
    Stateful deduplicator for Article objects.

    Usage::

        dedup = ArticleDeduplicator(checkpoint_path="data/seen_urls.json")
        dedup.load()

        unique = []
        for article in discovered_articles:
            if dedup.is_unique(article):
                unique.append(article)

        dedup.save()
    """

    def __init__(
        self,
        title_similarity_threshold: float = 92.0,
        checkpoint_path: Optional[Path] = None,
        enable_title_dedup: bool = True,
        # Maximum number of titles to compare (keep recent N for efficiency)
        max_title_cache: int = 10_000,
    ) -> None:
        self._threshold = title_similarity_threshold
        self._checkpoint = checkpoint_path
        self._enable_title_dedup = enable_title_dedup
        self._max_title_cache = max_title_cache

        # In-memory stores
        self._seen_urls: set[str] = set()
        self._seen_hashes: set[str] = set()
        self._seen_titles: list[str] = []  # ordered; most recent last

        self.stats = DeduplicationStats()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load checkpoint from disk if it exists."""
        if self._checkpoint and self._checkpoint.exists():
            try:
                data = json.loads(self._checkpoint.read_text(encoding="utf-8"))
                self._seen_urls = set(data.get("urls", []))
                self._seen_hashes = set(data.get("hashes", []))
                self._seen_titles = data.get("titles", [])
                logger.info(
                    "Loaded dedup checkpoint: %d URLs, %d hashes, %d titles",
                    len(self._seen_urls),
                    len(self._seen_hashes),
                    len(self._seen_titles),
                )
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Could not load dedup checkpoint: %s", exc)

    def save(self) -> None:
        """Persist current state to the checkpoint file."""
        if not self._checkpoint:
            return
        self._checkpoint.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "urls": list(self._seen_urls),
            "hashes": list(self._seen_hashes),
            "titles": self._seen_titles[-self._max_title_cache :],
        }
        try:
            self._checkpoint.write_text(
                json.dumps(data, indent=2), encoding="utf-8"
            )
            logger.debug("Dedup checkpoint saved to %s", self._checkpoint)
        except OSError as exc:
            logger.warning("Could not save dedup checkpoint: %s", exc)

    # ------------------------------------------------------------------
    # Core deduplication
    # ------------------------------------------------------------------

    def is_unique(self, article: Article) -> bool:
        """
        Return True if the article has not been seen before.
        Internally marks the article as seen when returning True.
        """
        self.stats.total_seen += 1

        # --- Stage 1: URL ---
        canonical = article.canonical_url or canonicalize_url(article.url)
        if canonical in self._seen_urls:
            self.stats.url_duplicates += 1
            logger.debug("URL duplicate: %s", article.url)
            return False

        # --- Stage 2: Content hash ---
        if article.content_hash and article.content_hash in self._seen_hashes:
            self.stats.hash_duplicates += 1
            logger.debug("Hash duplicate: %s", article.url)
            return False

        # --- Stage 3: Title similarity ---
        if self._enable_title_dedup and article.title:
            norm_title = _normalize_title(article.title)
            if self._is_title_duplicate(norm_title):
                self.stats.title_duplicates += 1
                logger.debug("Title duplicate: %s", article.title)
                return False

        # --- Accept ---
        self._mark_seen(article, canonical)
        self.stats.accepted += 1
        return True

    def add_many(self, articles: list[Article]) -> list[Article]:
        """Filter a list to unique articles only."""
        return [a for a in articles if self.is_unique(a)]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_title_duplicate(self, norm_title: str) -> bool:
        """Check if norm_title is similar to any previously seen title."""
        if len(norm_title) < 20:
            return False  # Too short to compare safely
        # Compare against recent titles (sliding window for performance)
        window = self._seen_titles[-min(500, len(self._seen_titles)) :]
        for seen in window:
            score = fuzz.token_sort_ratio(norm_title, seen)
            if score >= self._threshold:
                return True
        return False

    def _mark_seen(self, article: Article, canonical: str) -> None:
        self._seen_urls.add(canonical)
        if article.content_hash:
            self._seen_hashes.add(article.content_hash)
        if article.title:
            norm = _normalize_title(article.title)
            if len(self._seen_titles) >= self._max_title_cache:
                self._seen_titles = self._seen_titles[-(self._max_title_cache // 2) :]
            self._seen_titles.append(norm)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all in-memory state (does NOT delete checkpoint file)."""
        self._seen_urls.clear()
        self._seen_hashes.clear()
        self._seen_titles.clear()
        self.stats = DeduplicationStats()

    def __len__(self) -> int:
        return len(self._seen_urls)

    def __repr__(self) -> str:
        return f"<ArticleDeduplicator seen={len(self._seen_urls)} urls>"


def _normalize_title(title: str) -> str:
    """Lowercase and strip punctuation from a title for fuzzy comparison."""
    import re
    title = title.lower()
    title = re.sub(r"[^\w\s]", " ", title)
    title = re.sub(r"\s+", " ", title).strip()
    return title
