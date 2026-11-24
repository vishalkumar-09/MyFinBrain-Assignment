"""
sources/databases/cb_insights.py – CB Insights API adapter (optional).
"""
from __future__ import annotations
from typing import Iterator
from sources.base import Article, BaseSource
from sources import registry
from config.settings import CB_INSIGHTS_API_KEY
import logging

logger = logging.getLogger(__name__)


@registry.register
class CBInsightsSource(BaseSource):
    SOURCE_ID = "cb_insights"
    SOURCE_NAME = "CB Insights"

    def check_access(self) -> tuple[bool, str]:
        if not CB_INSIGHTS_API_KEY:
            return False, "CB_INSIGHTS_API_KEY not configured"
        return True, "API key present"

    def discover(self) -> Iterator[Article]:
        ok, msg = self.check_access()
        if not ok:
            self._logger.warning("CBInsightsSource disabled: %s", msg)
            self.health.record_error(msg)
            return
        self._logger.info("CBInsightsSource: implementation pending (Milestone 2)")
        return
        yield
