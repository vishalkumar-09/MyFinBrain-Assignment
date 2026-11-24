"""
sources/verification/startup_india.py
=====================================
Startup India directory verification adapter.

Used during geography and company verification to confirm Indian DPIIT-recognized
startups. Not an open RSS feed; provides verification lookups.
"""
from __future__ import annotations

import logging
from typing import Iterator

from sources.base import Article, BaseSource
from sources import registry

logger = logging.getLogger(__name__)


@registry.register
class StartupIndiaSource(BaseSource):
    SOURCE_ID = "startup_india"
    SOURCE_NAME = "Startup India"

    def check_access(self) -> tuple[bool, str]:
        return True, "Public portal (verification mode)"

    def discover(self) -> Iterator[Article]:
        self._logger.info("StartupIndiaSource is designated for verification rather than streaming discovery.")
        return
        yield
