"""
sources/verification/ycombinator.py
===================================
Y Combinator Portfolio directory verification adapter.
"""
from __future__ import annotations

import logging
from typing import Iterator

from sources.base import Article, BaseSource
from sources import registry

logger = logging.getLogger(__name__)


@registry.register
class YCombinatorSource(BaseSource):
    SOURCE_ID = "ycombinator"
    SOURCE_NAME = "Y Combinator Portfolio"

    def check_access(self) -> tuple[bool, str]:
        return True, "Public directory (verification lookup mode)"

    def discover(self) -> Iterator[Article]:
        self._logger.info("YCombinatorSource is designated for portfolio batch lookup and verification.")
        return
        yield
