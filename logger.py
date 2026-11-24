"""
Shared logging configuration for the entire project.

Call ``setup_logging()`` once at application startup (e.g. in main.py).
All other modules use ``logging.getLogger(__name__)`` normally.
"""
from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path

from config.settings import LOG_LEVEL, LOG_DIR


def setup_logging(
    level: str = LOG_LEVEL,
    log_dir: Path = LOG_DIR,
    console: bool = True,
    file_name: str = "pipeline.log",
) -> None:
    """
    Configure root logger with:
    - Console handler (stdout, coloured if supported)
    - Rotating file handler (1 MB per file, 5 backups)
    """
    root = logging.getLogger()
    root.setLevel(getattr(logging, level, logging.INFO))

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    if console:
        ch = logging.StreamHandler(sys.stdout)
        ch.setFormatter(fmt)
        root.addHandler(ch)

    log_dir.mkdir(parents=True, exist_ok=True)
    fh = logging.handlers.RotatingFileHandler(
        log_dir / file_name,
        maxBytes=1_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # Silence overly noisy third-party loggers
    for noisy in ("urllib3", "charset_normalizer", "feedparser"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
