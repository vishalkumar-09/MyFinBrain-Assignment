"""
sources/__init__.py – Source registry and auto-discovery.

Every concrete source adapter registers itself by calling
``registry.register(adapter_class)`` inside its module.  The registry is
populated lazily when ``get_all_sources()`` is first called.
"""

from __future__ import annotations

import importlib
import logging
from typing import TYPE_CHECKING, Type

if TYPE_CHECKING:
    from sources.base import BaseSource

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class _SourceRegistry:
    """Thread-safe registry for source adapter classes."""

    def __init__(self) -> None:
        self._adapters: dict[str, Type["BaseSource"]] = {}

    def register(self, adapter_class: Type["BaseSource"]) -> Type["BaseSource"]:
        """Register an adapter. Usable as a class decorator."""
        sid = adapter_class.SOURCE_ID
        if not sid:
            raise ValueError(f"{adapter_class.__name__} has no SOURCE_ID")
        if sid in self._adapters:
            logger.debug("Source '%s' re-registered (overriding).", sid)
        self._adapters[sid] = adapter_class
        logger.debug("Registered source adapter: %s", sid)
        return adapter_class

    def get(self, source_id: str) -> Type["BaseSource"] | None:
        return self._adapters.get(source_id)

    def all_ids(self) -> list[str]:
        return list(self._adapters.keys())

    def all_classes(self) -> list[Type["BaseSource"]]:
        return list(self._adapters.values())


registry = _SourceRegistry()

# ---------------------------------------------------------------------------
# Known adapter modules – import them so they self-register.
# ---------------------------------------------------------------------------
_ADAPTER_MODULES = [
    "sources.rss_source",
    "sources.google_news",
    "sources.news.techcrunch",
    "sources.news.crunchbase_news",
    "sources.news.inc42",
    "sources.news.entrackr",
    "sources.news.yourstory",
    "sources.news.ettech",
    "sources.news.businesswire",
    "sources.news.prnewswire",
    "sources.news.venturebeat",
    "sources.news.sifted",
    "sources.news.vccircle",
    "sources.databases.crunchbase",
    "sources.databases.tracxn",
    "sources.databases.dealroom",
    "sources.databases.pitchbook",
    "sources.databases.cb_insights",
    "sources.verification.sec_edgar",
    "sources.verification.startup_india",
    "sources.verification.mca",
    "sources.verification.ycombinator",
    "sources.verification.antler",
    "sources.verification.company_website",
]


def _load_adapters() -> None:
    """Import all adapter modules; failures are logged but non-fatal."""
    for mod_path in _ADAPTER_MODULES:
        try:
            importlib.import_module(mod_path)
        except ImportError as exc:
            logger.debug("Adapter module '%s' could not be imported: %s", mod_path, exc)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error loading adapter module '%s': %s", mod_path, exc)


_adapters_loaded = False


def get_all_sources() -> list[Type["BaseSource"]]:
    """Return all registered source adapter classes."""
    global _adapters_loaded
    if not _adapters_loaded:
        _load_adapters()
        _adapters_loaded = True
    return registry.all_classes()


def get_source(source_id: str) -> Type["BaseSource"] | None:
    global _adapters_loaded
    if not _adapters_loaded:
        _load_adapters()
        _adapters_loaded = True
    return registry.get(source_id)
