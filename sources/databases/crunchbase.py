"""
sources/databases/crunchbase.py
================================
Crunchbase API adapter (optional – requires API key).

When CRUNCHBASE_API_KEY is not configured, this adapter logs a warning and
yields nothing.  It does NOT scrape the Crunchbase website.

API documentation: https://data.crunchbase.com/docs
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Iterator

from sources.base import Article, BaseSource
from sources import registry
from config.settings import CRUNCHBASE_API_KEY, START_DATE, END_DATE, USER_AGENT

logger = logging.getLogger(__name__)


@registry.register
class CrunchbaseSource(BaseSource):
    SOURCE_ID = "crunchbase"
    SOURCE_NAME = "Crunchbase"

    _API_BASE = "https://api.crunchbase.com/api/v4"

    def check_access(self) -> tuple[bool, str]:
        if not CRUNCHBASE_API_KEY:
            return False, "CRUNCHBASE_API_KEY not configured"
        return True, "API key present"

    def discover(self) -> Iterator[Article]:
        ok, msg = self.check_access()
        if not ok:
            self._logger.warning("CrunchbaseSource disabled: %s", msg)
            self.health.record_error(msg)
            return
        # TODO (Milestone 2): implement paginated /searches/funding_rounds endpoint
        self._logger.info("CrunchbaseSource: API key found – implementation pending (Milestone 2)")
        return
        yield  # make this a generator
