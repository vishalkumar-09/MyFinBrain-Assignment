"""
discovery/collector.py
======================
Central discovery orchestrator for the pipeline.

Responsibilities:
- Run every enabled source adapter (optionally filtered by source ID).
- Apply cross-source article deduplication.
- Persist discovered articles to a checkpoint JSON file so the pipeline
  can resume without re-fetching already-processed URLs.
- Emit structured progress logs and a final ``DiscoveryResult`` summary.
- Isolate per-source failures so one broken adapter never stops the run.
- Support configurable concurrency (ThreadPoolExecutor).

The collector does NOT extract funding information — it only discovers and
deduplicates article URLs/metadata.  Extraction is handled in Milestone 3.
"""

from __future__ import annotations

import json
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from config.settings import (
    END_DATE,
    EXPORT_DIR,
    MAX_CONCURRENT_REQUESTS,
    REQUEST_DELAY_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    START_DATE,
    USER_AGENT,
)
from discovery.article_deduplicator import ArticleDeduplicator
from sources import get_all_sources, get_source
from sources.base import Article, SourceHealth

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class SourceResult:
    source_id: str
    articles: list[Article]
    health: SourceHealth
    unique_articles: int = 0  # filled in after global dedup


@dataclass
class DiscoveryResult:
    start_date: date
    end_date: date
    started_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    finished_at: Optional[datetime] = None

    source_results: list[SourceResult] = field(default_factory=list)

    total_discovered: int = 0
    total_unique: int = 0
    total_duplicate: int = 0
    total_errors: int = 0

    articles: list[Article] = field(default_factory=list)

    def finish(self) -> None:
        self.finished_at = datetime.now(timezone.utc)

    @property
    def duration_seconds(self) -> float:
        if self.finished_at is None:
            return 0.0
        return (self.finished_at - self.started_at).total_seconds()

    def print_summary(self) -> None:
        """Print a human-readable terminal summary."""
        sep = "=" * 65
        print(f"\n{sep}")
        print("DISCOVERY SUMMARY")
        print(sep)
        print(f"Date range  : {self.start_date} → {self.end_date}")
        print(f"Duration    : {self.duration_seconds:.1f}s")
        print(f"Sources run : {len(self.source_results)}")
        print(f"Articles discovered  : {self.total_discovered}")
        print(f"Unique articles kept : {self.total_unique}")
        print(f"Duplicates removed   : {self.total_duplicate}")
        print(f"Source errors        : {self.total_errors}")
        print("-" * 65)
        print(f"{'Source':<30} {'Found':>7} {'Unique':>7} {'Errors':>7}")
        print("-" * 65)
        for sr in sorted(
            self.source_results, key=lambda x: -x.unique_articles
        ):
            status = "✓" if sr.health.success else "✗"
            print(
                f"  {status} {sr.source_id:<28} "
                f"{sr.health.articles_found:>6} "
                f"{sr.unique_articles:>7} "
                f"{len(sr.health.errors):>7}"
            )
        print(sep)

    def to_dict(self) -> dict:
        return {
            "start_date": str(self.start_date),
            "end_date": str(self.end_date),
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "total_discovered": self.total_discovered,
            "total_unique": self.total_unique,
            "total_duplicate": self.total_duplicate,
            "total_errors": self.total_errors,
            "sources": [
                {
                    "source_id": sr.source_id,
                    "articles_found": sr.health.articles_found,
                    "unique_articles": sr.unique_articles,
                    "errors": sr.health.errors,
                    "success": sr.health.success,
                }
                for sr in self.source_results
            ],
        }


# ---------------------------------------------------------------------------
# Checkpoint persistence
# ---------------------------------------------------------------------------


class DiscoveryCheckpoint:
    """
    Persists discovered article URLs to a JSON file.

    On subsequent runs, already-discovered URLs are skipped so we don't
    re-fetch and re-process them.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._seen_urls: set[str] = set()
        self._lock = threading.Lock()

    def load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._seen_urls = set(data.get("urls", []))
                logger.info(
                    "Checkpoint loaded: %d previously seen URLs",
                    len(self._seen_urls),
                )
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Could not load checkpoint: %s", exc)

    def save(self, new_articles: list[Article]) -> None:
        """Add new articles and flush to disk."""
        with self._lock:
            for a in new_articles:
                url = a.canonical_url or a.url
                self._seen_urls.add(url)
            self._path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "url_count": len(self._seen_urls),
                "urls": list(self._seen_urls),
            }
            try:
                self._path.write_text(
                    json.dumps(data, indent=2), encoding="utf-8"
                )
            except OSError as exc:
                logger.warning("Could not save checkpoint: %s", exc)

    def was_seen(self, url: str) -> bool:
        return url in self._seen_urls

    def __len__(self) -> int:
        return len(self._seen_urls)


# ---------------------------------------------------------------------------
# Collector
# ---------------------------------------------------------------------------


class DiscoveryCollector:
    """
    Orchestrates multi-source article discovery.

    Workflow:
    1. Resolve source adapter classes (all or filtered by ID).
    2. Run each adapter, optionally in parallel threads.
    3. Apply ``ArticleDeduplicator`` across all sources.
    4. Skip articles already in the checkpoint (incremental mode).
    5. Return ``DiscoveryResult`` with per-source stats.
    """

    def __init__(
        self,
        start_date: date = START_DATE,
        end_date: date = END_DATE,
        source_ids: Optional[list[str]] = None,
        max_workers: int = MAX_CONCURRENT_REQUESTS,
        user_agent: str = USER_AGENT,
        request_delay: float = REQUEST_DELAY_SECONDS,
        timeout: int = REQUEST_TIMEOUT_SECONDS,
        checkpoint_path: Optional[Path] = None,
        dedup_checkpoint_path: Optional[Path] = None,
        incremental: bool = True,
        title_similarity_threshold: float = 92.0,
    ) -> None:
        self.start_date = start_date
        self.end_date = end_date
        self.source_ids = source_ids
        self.max_workers = max_workers
        self.user_agent = user_agent
        self.request_delay = request_delay
        self.timeout = timeout
        self.incremental = incremental
        self.title_threshold = title_similarity_threshold

        # Default checkpoint paths inside data/
        _data_dir = EXPORT_DIR
        self._checkpoint = DiscoveryCheckpoint(
            checkpoint_path or (_data_dir / "discovery_checkpoint.json")
        )
        self._deduplicator = ArticleDeduplicator(
            title_similarity_threshold=title_similarity_threshold,
            checkpoint_path=dedup_checkpoint_path
            or (_data_dir / "dedup_checkpoint.json"),
        )

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self) -> DiscoveryResult:
        result = DiscoveryResult(
            start_date=self.start_date,
            end_date=self.end_date,
        )

        # Load persisted checkpoints for incremental mode
        if self.incremental:
            self._checkpoint.load()
            self._deduplicator.load()

        source_classes = self._resolve_sources()
        if not source_classes:
            logger.warning("No source adapters found to run.")
            result.finish()
            return result

        logger.info(
            "Starting discovery: %d source(s) | %s → %s | workers=%d",
            len(source_classes),
            self.start_date,
            self.end_date,
            self.max_workers,
        )

        # Run sources
        source_results = self._run_sources(source_classes)

        # Global deduplication across all sources
        all_articles: list[Article] = []
        for sr in source_results:
            # Pre-filter: skip articles already in checkpoint
            if self.incremental:
                fresh = [
                    a
                    for a in sr.articles
                    if not self._checkpoint.was_seen(a.canonical_url or a.url)
                ]
                skipped = len(sr.articles) - len(fresh)
                if skipped:
                    logger.debug(
                        "%s: skipped %d already-seen articles", sr.source_id, skipped
                    )
                sr.articles = fresh

            # Cross-source dedup
            unique = self._deduplicator.add_many(sr.articles)
            sr.unique_articles = len(unique)
            all_articles.extend(unique)

        # Aggregate stats
        result.source_results = source_results
        result.articles = all_articles
        result.total_discovered = sum(
            sr.health.articles_found for sr in source_results
        )
        result.total_unique = len(all_articles)
        result.total_duplicate = (
            result.total_discovered - result.total_unique
        )
        result.total_errors = sum(
            len(sr.health.errors) for sr in source_results
        )

        # Persist updated checkpoints
        if self.incremental:
            self._checkpoint.save(all_articles)
            self._deduplicator.save()

        result.finish()
        logger.info(
            "Discovery complete: %d unique articles in %.1fs",
            result.total_unique,
            result.duration_seconds,
        )
        return result

    # ------------------------------------------------------------------
    # Source resolution and execution
    # ------------------------------------------------------------------

    def _resolve_sources(self):
        """Return filtered list of source adapter classes."""
        all_classes = get_all_sources()
        if self.source_ids is None:
            return all_classes
        resolved = []
        missing = []
        for sid in self.source_ids:
            cls = get_source(sid)
            if cls:
                resolved.append(cls)
            else:
                missing.append(sid)
        if missing:
            logger.warning(
                "Unknown source IDs (skipping): %s", ", ".join(missing)
            )
        return resolved

    def _run_sources(
        self, source_classes: list
    ) -> list[SourceResult]:
        """Run each source adapter; return list of SourceResult."""
        results: list[SourceResult] = []

        if self.max_workers <= 1:
            # Sequential execution (predictable, easier to debug)
            for cls in source_classes:
                sr = self._run_one_source(cls)
                results.append(sr)
        else:
            # Concurrent execution with bounded thread pool
            with ThreadPoolExecutor(
                max_workers=self.max_workers,
                thread_name_prefix="discovery",
            ) as executor:
                futures = {
                    executor.submit(self._run_one_source, cls): cls
                    for cls in source_classes
                }
                for future in as_completed(futures):
                    cls = futures[future]
                    try:
                        sr = future.result()
                        results.append(sr)
                    except Exception as exc:
                        sid = getattr(cls, "SOURCE_ID", str(cls))
                        logger.error(
                            "Source %s raised in executor: %s", sid, exc
                        )
                        from sources.base import SourceHealth

                        fake_health = SourceHealth(source_id=sid)
                        fake_health.record_error(str(exc))
                        fake_health.finish()
                        results.append(
                            SourceResult(
                                source_id=sid,
                                articles=[],
                                health=fake_health,
                            )
                        )
        return results

    def _run_one_source(self, cls) -> SourceResult:
        """Instantiate and run a single source adapter."""
        sid = getattr(cls, "SOURCE_ID", "unknown")
        logger.info("Running source: %s", sid)
        try:
            instance = cls(
                start_date=self.start_date,
                end_date=self.end_date,
                user_agent=self.user_agent,
                request_delay=self.request_delay,
                timeout=self.timeout,
            )
        except TypeError:
            # Some adapters (e.g. GoogleNewsSource) accept extra kwargs;
            # fall back to minimal init if signature doesn't match.
            instance = cls(
                start_date=self.start_date,
                end_date=self.end_date,
            )

        articles, health = instance.run()
        status = "✓" if health.success else "✗"
        logger.info(
            "[%s] %s: found=%d errors=%d",
            status,
            sid,
            health.articles_found,
            len(health.errors),
        )
        return SourceResult(
            source_id=sid,
            articles=articles,
            health=health,
        )
