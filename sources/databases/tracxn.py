"""
sources/databases/tracxn.py – Tracxn API adapter (optional).
"""
from __future__ import annotations
from typing import Iterator
from sources.base import Article, BaseSource
from sources import registry
from config.settings import TRACXN_API_KEY
import logging

logger = logging.getLogger(__name__)


@registry.register
class TracxnSource(BaseSource):
    SOURCE_ID = "tracxn"
    SOURCE_NAME = "Tracxn"

    def check_access(self) -> tuple[bool, str]:
        if not TRACXN_API_KEY:
            return False, "TRACXN_API_KEY not configured"
        return True, "API key present"

    def discover(self) -> Iterator[Article]:
        ok, msg = self.check_access()
        if not ok:
            self._logger.warning("TracxnSource disabled: %s", msg)
            self.health.record_error(msg)
            return
        self._logger.info("TracxnSource: implementation pending (Milestone 2)")
        return
        yield
