"""
config/settings.py
==================
Central configuration loaded from environment variables and .env file.
All tuneable knobs live here; no credentials or file paths are hardcoded
anywhere else in the project.
"""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env from project root (parent of config/)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env", override=False)


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


def _parse_date(value: str, fallback: date) -> date:
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return fallback


# ---------------------------------------------------------------------------
# Date range
# ---------------------------------------------------------------------------
START_DATE: date = _parse_date(
    _env("START_DATE", "2024-11-23"), date(2024, 11, 23)
)
END_DATE: date = _parse_date(
    _env("END_DATE", "2026-11-23"), date(2026, 11, 23)
)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASE_URL: str = _env("DATABASE_URL", f"sqlite:///{_PROJECT_ROOT}/data/startups_funding.sqlite")

# ---------------------------------------------------------------------------
# Networking & concurrency
# ---------------------------------------------------------------------------
MAX_CONCURRENT_REQUESTS: int = _env_int("MAX_CONCURRENT_REQUESTS", 5)
REQUEST_DELAY_SECONDS: float = _env_float("REQUEST_DELAY_SECONDS", 1.0)
REQUEST_TIMEOUT_SECONDS: int = _env_int("REQUEST_TIMEOUT_SECONDS", 30)
MAX_RETRIES: int = _env_int("MAX_RETRIES", 3)
USER_AGENT: str = _env(
    "USER_AGENT",
    "StartupFundingIntelligence/1.0 (research bot; contact@example.com)",
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL: str = _env("LOG_LEVEL", "INFO").upper()
LOG_DIR: Path = _PROJECT_ROOT / _env("LOG_DIR", "logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
EXPORT_DIR: Path = _PROJECT_ROOT / _env("EXPORT_DIR", "data")
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Optional API credentials (empty string = not configured)
# ---------------------------------------------------------------------------
OPENAI_API_KEY: str = _env("OPENAI_API_KEY")
OPENAI_MODEL: str = _env("OPENAI_MODEL", "gpt-4o-mini")
ANTHROPIC_API_KEY: str = _env("ANTHROPIC_API_KEY")
GOOGLE_API_KEY: str = _env("GOOGLE_API_KEY")
CRUNCHBASE_API_KEY: str = _env("CRUNCHBASE_API_KEY")
TRACXN_API_KEY: str = _env("TRACXN_API_KEY")
PITCHBOOK_EXPORT_PATH: str = _env("PITCHBOOK_EXPORT_PATH")
DEALROOM_API_KEY: str = _env("DEALROOM_API_KEY")
CB_INSIGHTS_API_KEY: str = _env("CB_INSIGHTS_API_KEY")

# ---------------------------------------------------------------------------
# Target countries
# ---------------------------------------------------------------------------
TARGET_COUNTRIES: list[str] = ["United States", "India"]

# ---------------------------------------------------------------------------
# Project root (useful for other modules)
# ---------------------------------------------------------------------------
PROJECT_ROOT: Path = _PROJECT_ROOT
