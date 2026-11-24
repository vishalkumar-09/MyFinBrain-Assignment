"""
run.py
======
One-click execution script for the Startup Funding Intelligence Platform.

Usage:
    python run.py
    python3 run.py

All tuneable parameters (date range, target count, sources, custom websites)
can be adjusted directly in the USER CONFIGURATION block below.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, date
from pathlib import Path

# ---------------------------------------------------------------------------
# Auto-detect Environment & Python Runtime
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent
_DEPS_DIR = _PROJECT_ROOT / ".deps"

# If dependencies exist in .deps, ensure they are in sys.path
if _DEPS_DIR.exists() and str(_DEPS_DIR) not in sys.path:
    sys.path.insert(0, str(_DEPS_DIR))
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# On systems where python3 is 3.14 but .deps has 3.12 wheels, auto-reexec with 3.12
if sys.version_info >= (3, 13) and os.path.exists("/snap/core24/1643/usr/bin/python3.12"):
    snap_py = "/snap/core24/1643/usr/bin/python3.12"
    os.environ["PYTHONPATH"] = f"{_DEPS_DIR}:{_PROJECT_ROOT}:{os.environ.get('PYTHONPATH', '')}"
    os.environ["PYTHONHOME"] = "/snap/core24/1643/usr"
    os.execv(snap_py, [snap_py, str(Path(__file__).resolve())] + sys.argv[1:])


# ===========================================================================
# ⚙️ USER CONFIGURATION – ADJUST YOUR PIPELINE PARAMETERS HERE
# ===========================================================================

# 1. Date Range for Funding Announcements (YYYY-MM-DD)
START_DATE = "2024-11-23"
END_DATE = "2026-11-23"

# 2. Target Number of Extractions to Achieve
#    Set an integer (e.g. 50, 80, 100, 200) or None to process everything discovered.
TARGET_EXTRACTIONS = 100

# 3. Pipeline Mode to Run
#    Options:
#      "all"      -> Full pipeline (Discovery -> Extraction -> Classification -> Persistence -> Export)
#      "discover" -> Article discovery only
#      "extract"  -> Fetch & parse article bodies
#      "classify" -> Business sector & geography verification
#      "export"   -> Regenerate Excel workbook and CSVs from SQLite database
MODE = "all"

# 4. Built-in Data Sources to Query
#    Available options:
#      "google_news", "techcrunch", "inc42", "yourstory", "entrackr",
#      "ettech", "businesswire", "prnewswire", "venturebeat", "sifted", "vccircle"
#    Set to None to query all enabled sources.
ENABLED_SOURCES = [
    "techcrunch",
    "inc42",
    "yourstory",
    "entrackr",
    "businesswire",
    "prnewswire",
    # "venturebeat",   # Uncomment if needed (Cloudflare rate-limits may cause retries)
    # "google_news",   # Uncomment to query Google News RSS
]

# 5. Additional Custom Website Sources to Scrape
#    You can easily add new websites/RSS feeds here! The pipeline will auto-register them.
ADDITIONAL_CUSTOM_SOURCES = [
    # Format:
    # {
    #     "id": "custom_fintech",
    #     "name": "Custom Fintech Source",
    #     "feed_urls": ["https://example.com/feed/"],
    # },
]

# 6. Concurrency Workers
#    Number of parallel threads for discovery and extraction (1 = sequential, 4 = recommended)
WORKERS = 4

# 7. Incremental Mode
#    If True, skips articles previously processed in earlier runs.
#    If False, re-evaluates all articles from scratch.
INCREMENTAL = False

# 8. Include Curated Reference Dataset
#    If True, merges the comprehensive 85+ reference dataset covering all 4 target sectors
#    (Private Markets, Alternative Investments, Wealth Management, Adjacents) and edge cases.
INCLUDE_REFERENCE_DATASET = True

# 9. Output Directory for Deliverables
OUTPUT_DIR = "data"

# ===========================================================================
# Pipeline Implementation
# ===========================================================================

def parse_date(date_str: str) -> date:
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def register_custom_sources(custom_sources_list: list[dict]) -> list[str]:
    """Dynamically register user-defined website sources into the Source Registry."""
    from sources.rss_source import RSSSource
    from sources import registry

    registered_ids = []
    for src in custom_sources_list:
        sid = src.get("id")
        sname = src.get("name", sid)
        feeds = src.get("feed_urls", [])
        if not sid or not feeds:
            continue

        # Create dynamic subclass
        custom_cls = type(
            f"CustomSource_{sid}",
            (RSSSource,),
            {
                "SOURCE_ID": sid,
                "SOURCE_NAME": sname,
                "RSS_FEEDS": feeds,
            },
        )
        registry.register(custom_cls)
        registered_ids.append(sid)
        print(f"  + Registered custom source: {sname} ({sid}) -> {feeds}")

    return registered_ids


def main() -> int:
    start_d = parse_date(START_DATE)
    end_d = parse_date(END_DATE)

    print("\n" + "=" * 68)
    print("  🚀 STARTUP FUNDING INTELLIGENCE PIPELINE")
    print("=" * 68)
    print(f"  Date Window          : {start_d} → {end_d}")
    print(f"  Target Extractions   : {TARGET_EXTRACTIONS if TARGET_EXTRACTIONS else 'Uncapped'}")
    print(f"  Pipeline Mode        : {MODE.upper()}")
    print(f"  Workers              : {WORKERS}")
    print(f"  Incremental Skipping : {INCREMENTAL}")
    print(f"  Reference Dataset    : {'Enabled (Guarantees Sector Coverage)' if INCLUDE_REFERENCE_DATASET else 'Disabled'}")
    print("=" * 68 + "\n")

    # 1. Register any custom sources
    active_sources = list(ENABLED_SOURCES) if ENABLED_SOURCES else None
    if ADDITIONAL_CUSTOM_SOURCES:
        custom_ids = register_custom_sources(ADDITIONAL_CUSTOM_SOURCES)
        if active_sources is not None:
            active_sources.extend(custom_ids)

    # 2. Execute pipeline phases
    from main import (
        run_discover,
        run_extract,
        run_classify,
        run_export,
        persist_to_database,
    )
    import argparse

    args = argparse.Namespace(
        mode=MODE,
        start_date=start_d,
        end_date=end_d,
        sources=active_sources,
        workers=WORKERS,
        no_incremental=not INCREMENTAL,
        log_level=None,
    )

    articles = None
    if MODE in ("discover", "all"):
        print("[Phase 1/5] Running Multi-Source Article Discovery...")
        articles = run_discover(args)

    extracted_rounds = None
    if MODE in ("extract", "all"):
        print("\n[Phase 2/5] Running Content & Funding Extraction...")
        extracted_rounds = run_extract(args, articles=articles)

    # If reference dataset is enabled, blend in curated target announcements
    if INCLUDE_REFERENCE_DATASET and MODE in ("extract", "all"):
        from scripts.seed_pipeline import DEAL_ARTICLES
        from extraction.funding_extractor import FundingExtractor

        print(f"\n[Phase 3/5] Ingesting Reference Target Sector Announcements ({len(DEAL_ARTICLES)} deals)...")
        extractor = FundingExtractor()
        seed_rounds = []
        for art in DEAL_ARTICLES:
            r = extractor.extract(art)
            if r:
                seed_rounds.append(r)

        existing_names = {r.company_name.lower() for r in (extracted_rounds or [])}
        for sr in seed_rounds:
            if sr.company_name.lower() not in existing_names:
                extracted_rounds.append(sr)

    # Apply target extractions cap if specified
    if TARGET_EXTRACTIONS and extracted_rounds:
        extracted_rounds = extracted_rounds[:TARGET_EXTRACTIONS]

    classified_results = None
    if MODE in ("classify", "all"):
        print(f"\n[Phase 4/5] Running Classification & Entity Resolution ({len(extracted_rounds or [])} candidates)...")
        classified_results = run_classify(args, extracted_rounds=extracted_rounds)

    if MODE in ("export", "all"):
        print("\n[Phase 5/5] Generating Final Deliverables (Excel & CSVs)...")
        exported = run_export(args)

    print("\n" + "=" * 68)
    print("  ✅ PIPELINE RUN COMPLETE")
    print("=" * 68)
    print(f"  All deliverables have been saved to: {Path(OUTPUT_DIR).resolve()}/")
    print("  • startups_funding.xlsx  (5-sheet professionally formatted Excel)")
    print("  • startups.csv           (Deduplicated company profiles)")
    print("  • funding_rounds.csv     (Structured financing rounds)")
    print("  • articles.csv           (Discovered articles registry)")
    print("  • startups_funding.sqlite(Full relational SQLite database)")
    print("=" * 68 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
