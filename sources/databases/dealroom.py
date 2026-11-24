"""
sources/databases/dealroom.py – Dealroom API adapter (optional).
"""
from __future__ import annotations
from typing import Iterator
from sources.base import Article, BaseSource
from sources import registry
from config.settings import DEALROOM_API_KEY
import logging

logger = logging.getLogger(__name__)


@registry.register
class DealroomSource(BaseSource):
    SOURCE_ID = "dealroom"
    SOURCE_NAME = "Dealroom"

    def check_access(self) -> tuple[bool, str]:
        if not DEALROOM_API_KEY:
            return False, "DEALROOM_API_KEY not configured"
        return True, "API key present"

    def discover(self) -> Iterator[Article]:
        ok, msg = self.check_access()
        if not ok:
            self._logger.warning("DealroomSource disabled: %s", msg)
            self.health.record_error(msg)
            return
        self._logger.info("DealroomSource: implementation pending (Milestone 2)")
        return
        yield
