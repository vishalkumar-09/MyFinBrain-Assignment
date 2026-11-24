"""
sources/databases/pitchbook.py – PitchBook export adapter (optional).

PitchBook does not offer a public API.  Users can export data from the
PitchBook web app and configure PITCHBOOK_EXPORT_PATH to point to the file.
"""
from __future__ import annotations
from typing import Iterator
from sources.base import Article, BaseSource
from sources import registry
from config.settings import PITCHBOOK_EXPORT_PATH
import logging

logger = logging.getLogger(__name__)


@registry.register
class PitchBookSource(BaseSource):
    SOURCE_ID = "pitchbook"
    SOURCE_NAME = "PitchBook"

    def check_access(self) -> tuple[bool, str]:
        if not PITCHBOOK_EXPORT_PATH:
            return False, "PITCHBOOK_EXPORT_PATH not configured"
        from pathlib import Path
        p = Path(PITCHBOOK_EXPORT_PATH)
        if not p.exists():
            return False, f"Export file not found: {PITCHBOOK_EXPORT_PATH}"
        return True, f"Export file found: {PITCHBOOK_EXPORT_PATH}"

    def discover(self) -> Iterator[Article]:
        ok, msg = self.check_access()
        if not ok:
            self._logger.warning("PitchBookSource disabled: %s", msg)
            self.health.record_error(msg)
            return
        self._logger.info("PitchBookSource: CSV/Excel parsing pending (Milestone 2)")
        return
        yield
