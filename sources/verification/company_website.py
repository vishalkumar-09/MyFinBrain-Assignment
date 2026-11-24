"""
sources/verification/company_website.py
========================================
Company website verifier.

Given a company website URL, this module fetches the homepage and About page
to extract a canonical description and confirm the company's country of
incorporation or headquarters.

Used in the classification and geography verification phases, not for
primary article discovery.
"""
from __future__ import annotations

import logging
from typing import Iterator

from sources.base import Article, BaseSource
from sources import registry

logger = logging.getLogger(__name__)


@registry.register
class CompanyWebsiteSource(BaseSource):
    """
    Verification adapter: not used for discovery.
    The actual verification logic lives in classification/geography_classifier.py.
    This stub exists so the registry is complete.
    """

    SOURCE_ID = "company_website"
    SOURCE_NAME = "Company Website"

    def discover(self) -> Iterator[Article]:
        # This adapter is not used in the discovery phase.
        self._logger.debug("CompanyWebsiteSource is a verification-only adapter.")
        return
        yield
