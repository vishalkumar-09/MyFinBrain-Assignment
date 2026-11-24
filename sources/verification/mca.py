"""
sources/verification/mca.py
===========================
Ministry of Corporate Affairs (MCA India) corporate registry verification adapter.

Used during geography and corporate entity verification to look up CIN and incorporation details.
"""
from __future__ import annotations

import logging
from typing import Iterator

from sources.base import Article, BaseSource
from sources import registry

logger = logging.getLogger(__name__)


@registry.register
class MCASource(BaseSource):
    SOURCE_ID = "mca"
    SOURCE_NAME = "Ministry of Corporate Affairs (India)"

    def check_access(self) -> tuple[bool, str]:
        return True, "Government portal (verification lookup mode)"

    def discover(self) -> Iterator[Article]:
        self._logger.info("MCASource is designated for corporate identity verification rather than RSS discovery.")
        return
        yield
