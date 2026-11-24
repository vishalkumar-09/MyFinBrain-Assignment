"""
sources/verification/sec_edgar.py
==================================
SEC EDGAR full-text search adapter.

Uses the publicly available EFTS (EDGAR Full-Text Search) API to find
Form D filings (private placement notices) for US companies.
No authentication required.  Rate limit: ≤10 req/s.

API: https://efts.sec.gov/LATEST/search-index?q=%22private+equity%22&dateRange=custom&startdt=...&enddt=...&forms=D
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Iterator

from sources.base import Article, BaseSource
from sources import registry
from config.settings import START_DATE, END_DATE, USER_AGENT, REQUEST_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

_EFTS_URL = "https://efts.sec.gov/LATEST/search-index"


@registry.register
class SECEdgarSource(BaseSource):
    SOURCE_ID = "sec_edgar"
    SOURCE_NAME = "SEC EDGAR"

    def __init__(
        self,
        start_date: date = START_DATE,
        end_date: date = END_DATE,
        user_agent: str = USER_AGENT,
        timeout: int = REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        super().__init__(
            start_date=start_date,
            end_date=end_date,
            user_agent=user_agent,
            request_delay=0.5,  # SEC allows 10 req/s
            timeout=timeout,
        )

    def discover(self) -> Iterator[Article]:
        """Yield Form D filing articles from EDGAR EFTS."""
        params = {
            "q": '"venture capital" OR "private equity" OR "wealth management"',
            "forms": "D",
            "dateRange": "custom",
            "startdt": self.start_date.isoformat(),
            "enddt": self.end_date.isoformat(),
            "_source": "file_date,period_of_report,display_names,entity_name,file_num",
            "from": 0,
            "size": 50,
        }

        page = 0
        while True:
            params["from"] = page * 50
            resp = self._get(_EFTS_URL, params=params)
            if resp is None:
                break
            try:
                data = resp.json()
            except Exception as exc:
                self._logger.error("EDGAR JSON parse error: %s", exc)
                break

            hits = data.get("hits", {}).get("hits", [])
            if not hits:
                break

            for hit in hits:
                src = hit.get("_source", {})
                entity = src.get("entity_name", "Unknown Entity")
                file_num = src.get("file_num", "")
                file_date = src.get("file_date", "")
                url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&filenum={file_num}&type=D&dateb=&owner=include&count=10"

                published_at = None
                if file_date:
                    try:
                        published_at = datetime.strptime(file_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    except ValueError:
                        pass

                yield Article(
                    url=url,
                    title=f"SEC Form D Filing: {entity}",
                    source_id=self.SOURCE_ID,
                    source_name=self.SOURCE_NAME,
                    summary=f"Private placement filing by {entity}. File number: {file_num}.",
                    published_at=published_at,
                )

            if len(hits) < 50:
                break
            page += 1
