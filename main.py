"""
main.py
========
Entry point for the Startup Funding Intelligence pipeline.

Usage:
    python main.py --mode discover
    python main.py --mode extract
    python main.py --mode classify
    python main.py --mode all
    python main.py --mode export
    python main.py --mode all --start-date 2024-11-23 --end-date 2026-11-23
    python main.py --mode discover --sources techcrunch,inc42,google_news
    python main.py --mode discover --workers 3
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, datetime, timezone

from logger import setup_logging
from config.settings import START_DATE, END_DATE, EXPORT_DIR

setup_logging()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# CLI argument parsing
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="startup-funding-intelligence",
        description="Startup Funding Intelligence Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--mode",
        choices=["discover", "extract", "classify", "all", "export"],
        default="all",
        help="Pipeline mode to run (default: all)",
    )
    parser.add_argument(
        "--start-date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=START_DATE,
        metavar="YYYY-MM-DD",
        help=f"Start date for funding discovery (default: {START_DATE})",
    )
    parser.add_argument(
        "--end-date",
        type=lambda s: datetime.strptime(s, "%Y-%m-%d").date(),
        default=END_DATE,
        metavar="YYYY-MM-DD",
        help=f"End date for funding discovery (default: {END_DATE})",
    )
    parser.add_argument(
        "--sources",
        type=lambda s: [x.strip() for x in s.split(",")],
        default=None,
        metavar="SOURCE_IDS",
        help="Comma-separated list of source IDs to run (default: all enabled)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        metavar="N",
        help="Concurrent source workers (default: 1 = sequential)",
    )
    parser.add_argument(
        "--no-incremental",
        action="store_true",
        default=False,
        help="Disable incremental mode (re-process all articles)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        help="Override log level",
    )

    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Mode implementations
# ---------------------------------------------------------------------------

def run_discover(args) -> None:
    """
    Discovery phase: collect articles from all configured sources.
    Uses DiscoveryCollector which handles concurrency, dedup, checkpointing.
    """
    from discovery.collector import DiscoveryCollector

    collector = DiscoveryCollector(
        start_date=args.start_date,
        end_date=args.end_date,
        source_ids=args.sources,
        max_workers=args.workers,
        incremental=not args.no_incremental,
    )
    result = collector.run()

    # Persist the discovery result summary
    summary_path = EXPORT_DIR / "discovery_result.json"
    try:
        summary_path.write_text(
            json.dumps(result.to_dict(), indent=2), encoding="utf-8"
        )
        logger.info("Discovery summary saved to %s", summary_path)
    except OSError as exc:
        logger.warning("Could not save discovery summary: %s", exc)

    result.print_summary()

    # Persist discovered articles to database
    try:
        from database.repository import DatabaseRepository
        repo = DatabaseRepository()
        for art in result.articles:
            repo.save_article(
                url=art.url,
                canonical_url=art.canonical_url,
                title=art.title,
                source_name=art.source_name,
                published_at=art.published_at,
                article_text=art.full_text or art.summary,
                extraction_status=art.extraction_status.value if hasattr(art.extraction_status, "value") else str(art.extraction_status),
            )
    except Exception as exc:
        logger.debug("Could not save discovered articles to database: %s", exc)

    return result.articles


def run_extract(args, articles=None) -> list:
    """
    Extraction phase: fetch full text for articles and extract structured funding details.
    """
    from extraction.article_parser import ArticleParser
    from extraction.funding_extractor import FundingExtractor

    logger.info("=== EXTRACT mode ===")
    
    # If no articles provided in-memory, load discovered articles from checkpoint or discover
    if articles is None:
        from discovery.collector import DiscoveryCollector
        collector = DiscoveryCollector(
            start_date=args.start_date,
            end_date=args.end_date,
            source_ids=args.sources,
            max_workers=args.workers,
            incremental=not args.no_incremental,
        )
        discovery_result = collector.run()
        articles = discovery_result.articles

    logger.info("Extracting funding details from %d discovered articles...", len(articles))
    parser = ArticleParser()
    extractor = FundingExtractor()

    extracted_rounds = []
    vc_funds_filtered = 0
    companies_seen = set()

    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _process_one_article(article):
        if not article.full_text:
            parser.extract_article(article)
        # Filter out articles whose parsed publication date falls outside the target window
        if article.published_at:
            pub_d = article.published_at.date() if hasattr(article.published_at, "date") else article.published_at
            if pub_d < args.start_date or pub_d > args.end_date:
                return article, None
        rnd = extractor.extract(article)
        if rnd:
            deal_d = rnd.announcement_date or rnd.article_publication_date
            if deal_d and (deal_d < args.start_date or deal_d > args.end_date):
                return article, None
        return article, rnd

    workers = min(8, max(2, (args.workers or 1) * 2))
    processed_articles = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_process_one_article, art): art for art in articles}
        for future in as_completed(futures):
            try:
                art, round_data = future.result()
                processed_articles.append(art)
                if round_data:
                    if round_data.is_vc_fund_raise:
                        vc_funds_filtered += 1
                        logger.debug("Filtered out VC fund raise: %s", round_data.article_title)
                    else:
                        extracted_rounds.append(round_data)
                        companies_seen.add(round_data.company_name.lower())
            except Exception as exc:
                art = futures[future]
                logger.warning("Error extracting from %s: %s", art.url, exc)

    # Update article extraction statuses & dates in SQLite database
    try:
        from database.repository import DatabaseRepository
        repo = DatabaseRepository()
        for art in processed_articles:
            repo.save_article(
                url=art.url,
                canonical_url=art.canonical_url or art.url,
                title=art.title,
                source_name=art.source_name,
                published_at=art.published_at,
                article_text=art.full_text or art.summary,
                content_hash=art.content_hash,
                extraction_status=art.extraction_status.value if hasattr(art.extraction_status, "value") else str(art.extraction_status),
            )
    except Exception as exc:
        logger.debug("Could not update extracted articles in database: %s", exc)

    # Terminal summary
    sep = "=" * 65
    print(f"\n{sep}")
    print("EXTRACTION SUMMARY")
    print(sep)
    print(f"Articles processed           : {len(articles)}")
    print(f"Funding rounds identified    : {len(extracted_rounds)}")
    print(f"Unique companies identified  : {len(companies_seen)}")
    print(f"VC fund raises filtered out  : {vc_funds_filtered}")
    print(sep)

    # Persist extracted rounds
    extracted_path = EXPORT_DIR / "extracted_rounds.json"
    try:
        data = [r.model_dump(mode="json") if hasattr(r, "model_dump") else r for r in extracted_rounds]
        extracted_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        logger.info("Extracted rounds saved to %s", extracted_path)
    except OSError as exc:
        logger.warning("Could not save extracted rounds: %s", exc)

    return extracted_rounds


def run_classify(args, extracted_rounds=None) -> list:
    """
    Classification phase: evaluate business model and verify headquarters against US & India scope.
    """
    from classification.business_classifier import BusinessClassifier, RelevanceStatus
    from classification.geography_classifier import GeographyClassifier, GeoStatus
    from classification.relevance_scorer import RelevanceScorer
    from extraction.article_parser import ArticleParser
    from extraction.funding_extractor import ExtractedFundingRound
    from sources.verification.company_website import verify_company_hq_live

    logger.info("=== CLASSIFY mode ===")

    # Load extracted rounds if not provided in-memory
    if extracted_rounds is None:
        extracted_path = EXPORT_DIR / "extracted_rounds.json"
        if extracted_path.exists():
            try:
                raw_data = json.loads(extracted_path.read_text(encoding="utf-8"))
                extracted_rounds = [ExtractedFundingRound(**d) for d in raw_data]
            except Exception as exc:
                logger.warning("Could not read %s: %s", extracted_path, exc)
                extracted_rounds = []
        else:
            extracted_rounds = run_extract(args)

    logger.info("Classifying %d funding announcements...", len(extracted_rounds))
    biz_classifier = BusinessClassifier()
    geo_classifier = GeographyClassifier()
    scorer = RelevanceScorer()
    verify_parser = ArticleParser(timeout=10)
    hq_cache: dict[str, tuple] = {}

    classified_results = []
    stats = {
        "DIRECT_MATCH": 0,
        "ADJACENT_MATCH": 0,
        "NOT_RELEVANT": 0,
        "NEEDS_REVIEW": 0,
    }

    for rnd in extracted_rounds:
        lead_context = "\n".join(
            part for part in (rnd.article_title, rnd.company_description, (rnd.article_excerpt or "")[:700]) if part
        )
        full_context = "\n".join(
            part for part in (rnd.article_title, rnd.company_description, rnd.article_excerpt) if part
        )
        biz_result = biz_classifier.classify(
            company_name=rnd.company_name,
            description=rnd.company_description,
            article_text=lead_context,
        )
        geo_result = geo_classifier.verify(
            company_name=rnd.company_name,
            extracted_city=rnd.headquarters_city,
            extracted_country=rnd.headquarters_country,
            article_text=full_context,
        )

        # If sector matches but primary article omitted HQ or city, check official website / corroborating live coverage
        if (
            biz_result.relevance_status in (RelevanceStatus.DIRECT_MATCH, RelevanceStatus.ADJACENT_MATCH)
            and (geo_result.status == GeoStatus.NEEDS_REVIEW or (geo_result.status == GeoStatus.VERIFIED and not geo_result.headquarters_city))
        ):
            cache_key = rnd.company_name.lower()
            if cache_key not in hq_cache:
                sector_hint = (biz_result.supporting_evidence[0] if biz_result.supporting_evidence else None) or biz_result.primary_category
                hq_cache[cache_key] = verify_company_hq_live(
                    company_name=rnd.company_name,
                    geo_classifier=geo_classifier,
                    article_parser=verify_parser,
                    website=rnd.company_website,
                    lead_investor=rnd.lead_investor,
                    sector_hint=sector_hint,
                )
            verified_geo, corr_url = hq_cache[cache_key]
            if verified_geo is not None and (
                geo_result.status == GeoStatus.NEEDS_REVIEW
                or verified_geo.status == GeoStatus.OUT_OF_SCOPE
                or (verified_geo.headquarters_country == geo_result.headquarters_country and verified_geo.headquarters_city)
            ):
                geo_result = verified_geo
                if corr_url:
                    rnd.supporting_evidence["hq_corroboration"] = corr_url

        score_result = scorer.score(business=biz_result, geography=geo_result)

        stats[score_result.final_status] = stats.get(score_result.final_status, 0) + 1

        record = {
            "company_name": rnd.company_name,
            "company_website": rnd.company_website,
            "company_description": rnd.company_description,
            "headquarters_country": geo_result.headquarters_country or rnd.headquarters_country,
            "headquarters_city": geo_result.headquarters_city or rnd.headquarters_city,
            "operating_countries": geo_result.operating_countries,
            "funding_stage": rnd.funding_stage,
            "funding_amount": rnd.funding_amount,
            "currency": rnd.currency,
            "original_amount_text": rnd.original_amount_text,
            "lead_investor": rnd.lead_investor,
            "investors": rnd.investors,
            "primary_category": biz_result.primary_category,
            "secondary_categories": biz_result.secondary_categories,
            "relevance_status": score_result.final_status,
            "relevance_score": score_result.relevance_score,
            "confidence_score": score_result.confidence_score,
            "qualification_reason": score_result.summary_reason,
            "announcement_date": rnd.announcement_date,
            "article_publication_date": rnd.article_publication_date,
            "supporting_evidence": rnd.supporting_evidence,
            "source_url": rnd.source_url,
            "source_name": rnd.source_name,
            "article_title": rnd.article_title,
        }
        classified_results.append(record)

    # Terminal summary
    sep = "=" * 65
    print(f"\n{sep}")
    print("CLASSIFICATION SUMMARY")
    print(sep)
    print(f"Total candidates evaluated   : {len(extracted_rounds)}")
    print(f"Direct matches (Tier A/B/C)  : {stats.get('DIRECT_MATCH', 0)}")
    print(f"Adjacent matches (Tier D)    : {stats.get('ADJACENT_MATCH', 0)}")
    print(f"Records requiring review     : {stats.get('NEEDS_REVIEW', 0)}")
    print(f"Not relevant / Out of scope  : {stats.get('NOT_RELEVANT', 0) + stats.get('OUT_OF_SCOPE_GEOGRAPHY', 0)}")
    print(sep)

    # Persist classified records
    classified_path = EXPORT_DIR / "classified_startups.json"
    try:
        classified_path.write_text(json.dumps(classified_results, indent=2, default=str), encoding="utf-8")
        logger.info("Classified startups saved to %s", classified_path)
    except OSError as exc:
        logger.warning("Could not save classified startups: %s", exc)

    # Persist and deduplicate to SQLite database
    persist_to_database(classified_results)

    return classified_results


def persist_to_database(classified_records: list[dict]) -> None:
    """
    Persist classified startups, rounds, and evidence to SQLite database with entity resolution.
    """
    from database.repository import DatabaseRepository
    from database.models import Company, FundingRound
    from processing.normalizer import normalize_company_name, extract_website_domain
    from processing.entity_resolution import CompanyEntityResolver
    from processing.deduplicator import FundingRoundDeduplicator
    from datetime import datetime, date, timezone

    repo = DatabaseRepository()
    entity_resolver = CompanyEntityResolver()
    round_deduplicator = FundingRoundDeduplicator()

    existing_companies = repo.get_all_companies()
    companies_merged = 0
    rounds_merged = 0

    for rec in classified_records:
        comp_name = rec["company_name"]
        website = rec.get("company_website")
        domain = extract_website_domain(website)
        country = rec.get("headquarters_country")
        city = rec.get("headquarters_city")

        # Entity resolution for company
        matched_comp, conf, match_reason = entity_resolver.resolve(
            name=comp_name,
            website=website,
            country=country,
            city=city,
            existing_companies=existing_companies,
        )

        if matched_comp:
            company = matched_comp
            companies_merged += 1
            changed = False
            # Enrich missing attributes or upgrade NEEDS_REVIEW when corroborating article verifies HQ/category
            if not company.website and website:
                company.website = website
                company.website_domain = domain
                changed = True
            if not company.description and rec.get("company_description"):
                company.description = rec["company_description"]
                changed = True
            if not company.headquarters_country and country:
                company.headquarters_country = country
                changed = True
            if not company.headquarters_city and city:
                company.headquarters_city = city
                changed = True
            if rec.get("relevance_status") in ("DIRECT_MATCH", "ADJACENT_MATCH") and company.relevance_status in ("NEEDS_REVIEW", "NOT_RELEVANT", None):
                company.relevance_status = rec["relevance_status"]
                company.classification_confidence = max(company.classification_confidence or 0.0, rec.get("confidence_score", 0.0))
                if rec.get("primary_category"):
                    company.primary_category = rec["primary_category"]
                if rec.get("secondary_categories"):
                    company.secondary_categories = rec["secondary_categories"]
                changed = True
            elif not company.primary_category and rec.get("primary_category"):
                company.primary_category = rec["primary_category"]
                changed = True
            if changed:
                company = repo.save_company(company)
        else:
            company = Company(
                canonical_name=comp_name,
                normalized_name=normalize_company_name(comp_name),
                website=website,
                website_domain=domain,
                description=rec.get("company_description"),
                headquarters_country=country,
                headquarters_city=city,
                operating_countries=rec.get("operating_countries", []),
                primary_category=rec.get("primary_category"),
                secondary_categories=rec.get("secondary_categories", []),
                relevance_status=rec.get("relevance_status", "NOT_RELEVANT"),
                classification_confidence=rec.get("confidence_score", 0.0),
            )
            company = repo.save_company(company)
            existing_companies.append(company)

        # Parse date if present
        ann_date = None
        raw_ann_date = rec.get("announcement_date")
        if raw_ann_date:
            try:
                ann_date = date.fromisoformat(str(raw_ann_date))
            except Exception:
                pass

        # Deduplicate funding round
        existing_rounds = repo.get_funding_rounds_for_company(company.id)
        matched_round, round_reason = round_deduplicator.find_matching_round(
            company_id=company.id,
            stage=rec.get("funding_stage", "Other"),
            amount=rec.get("funding_amount"),
            currency=rec.get("currency"),
            announcement_date=ann_date,
            existing_rounds=existing_rounds,
        )

        if matched_round:
            funding_round = matched_round
            rounds_merged += 1
            round_changed = False
            if not funding_round.amount and rec.get("funding_amount"):
                funding_round.amount = rec["funding_amount"]
                funding_round.currency = rec.get("currency")
                funding_round.original_amount_text = rec.get("original_amount_text")
                round_changed = True
            if funding_round.funding_stage in ("Other", "Undisclosed") and rec.get("funding_stage") not in ("Other", "Undisclosed", None):
                funding_round.funding_stage = rec["funding_stage"]
                round_changed = True
            if not funding_round.announcement_date and ann_date:
                funding_round.announcement_date = ann_date
                round_changed = True
            if not funding_round.lead_investor and rec.get("lead_investor"):
                funding_round.lead_investor = rec["lead_investor"]
                round_changed = True
            new_invs = rec.get("investors") or []
            if new_invs:
                existing_invs = list(funding_round.investors or [])
                merged_invs = list(existing_invs)
                for inv in new_invs:
                    if inv.lower() not in {x.lower() for x in merged_invs}:
                        merged_invs.append(inv)
                if merged_invs != existing_invs:
                    funding_round.investors = merged_invs
                    round_changed = True
            if round_changed:
                funding_round = repo.save_funding_round(funding_round)
        else:
            funding_round = FundingRound(
                company_id=company.id,
                funding_stage=rec.get("funding_stage", "Other"),
                amount=rec.get("funding_amount"),
                currency=rec.get("currency"),
                original_amount_text=rec.get("original_amount_text"),
                announcement_date=ann_date,
                lead_investor=rec.get("lead_investor"),
                investors=rec.get("investors", []),
            )
            funding_round = repo.save_funding_round(funding_round)

        # Parse article publication date
        pub_dt = None
        raw_pub = rec.get("article_publication_date") or rec.get("published_at")
        if raw_pub:
            if isinstance(raw_pub, datetime):
                pub_dt = raw_pub
            elif isinstance(raw_pub, date):
                pub_dt = datetime.combine(raw_pub, datetime.min.time(), tzinfo=timezone.utc)
            elif isinstance(raw_pub, str):
                try:
                    pub_dt = datetime.fromisoformat(raw_pub).astimezone(timezone.utc)
                except Exception:
                    pass

        # Save article if present
        saved_art = None
        if rec.get("source_url"):
            saved_art = repo.save_article(
                url=rec["source_url"],
                canonical_url=rec["source_url"],
                title=rec.get("article_title", "Funding Announcement"),
                source_name=rec.get("source_name", "Unknown"),
                published_at=pub_dt,
            )

        # Save field-level evidence
        evidence_dict = rec.get("supporting_evidence", {})
        if isinstance(evidence_dict, dict):
            for field_name, evidence_text in evidence_dict.items():
                repo.save_evidence(
                    field_name=field_name,
                    evidence_text=evidence_text,
                    company_id=company.id,
                    funding_round_id=funding_round.id,
                    article_id=saved_art.id if saved_art else None,
                )

    logger.info(
        "Database persistence complete: %d companies resolved (%d merged), %d rounds (%d deduplicated)",
        len(existing_companies),
        companies_merged,
        len(classified_records),
        rounds_merged,
    )


def run_export(args) -> dict:
    """
    Export phase: generate startups.csv, funding_rounds.csv, articles.csv, and startups_funding.xlsx.
    """
    from export.exporter import DataExporter

    logger.info("=== EXPORT mode ===")
    exporter = DataExporter()
    exported_files = exporter.export_all()

    sep = "=" * 65
    print(f"\n{sep}")
    print("EXPORT DELIVERABLES SUMMARY")
    print(sep)
    for name, path in exported_files.items():
        size_kb = path.stat().st_size / 1024 if path.exists() else 0.0
        print(f"  ✓ {path.name:<28} ({size_kb:.1f} KB)")
    print(f"  ✓ startups_funding.sqlite      (SQLite database)")
    print(sep)
    return exported_files


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.log_level:
        logging.getLogger().setLevel(args.log_level)

    if args.start_date > args.end_date:
        logger.error("--start-date must be before --end-date")
        return 1

    logger.info("Startup Funding Intelligence Pipeline starting")
    logger.info(
        "Mode: %s | %s → %s | workers=%d",
        args.mode, args.start_date, args.end_date, args.workers,
    )

    try:
        articles = None
        if args.mode in ("discover", "all"):
            articles = run_discover(args)
        extracted_rounds = None
        if args.mode in ("extract", "all"):
            extracted_rounds = run_extract(args, articles=articles)
        if args.mode in ("classify", "all"):
            run_classify(args, extracted_rounds=extracted_rounds)
        if args.mode in ("export", "all"):
            run_export(args)
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user.")
        return 130

    logger.info("Pipeline complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
