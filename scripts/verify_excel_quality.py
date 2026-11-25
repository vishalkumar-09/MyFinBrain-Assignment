"""
scripts/verify_excel_quality.py
================================
Post-run quality check script for startups_funding.xlsx.

Checks:
  1. No blank Country, City, Lead Investor, Source URL, Primary Category, or Funding Announcement Date
  2. All announcement dates are strictly within 2026-07-01 to 2026-11-25
  3. No search/placeholder URLs in Source URL column
  4. Only United States and India companies on Funding Announcements sheet
  5. Optional ``--check-urls`` flag performs live HTTP GET check on every Source URL
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import openpyxl
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".deps"))
    import openpyxl

EXCEL_PATH = Path(__file__).resolve().parents[1] / "data" / "startups_funding.xlsx"
START_DATE = "2026-07-01"
END_DATE = "2026-11-25"

SEARCH_PATTERNS = ["?s=", "?searchType=", "search?q=", "/search?", "?q=", "?query=", "/?s="]


def run_checks(check_urls: bool = False) -> bool:
    if not EXCEL_PATH.exists():
        print(f"ERROR: Excel file not found at {EXCEL_PATH}")
        return False

    wb = openpyxl.load_workbook(str(EXCEL_PATH))
    sheet_names = wb.sheetnames
    print(f"Sheets found: {sheet_names}")

    if "Funding Announcements" not in sheet_names:
        print("ERROR: 'Funding Announcements' sheet missing!")
        return False

    ws = wb["Funding Announcements"]
    headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    print(f"Headers: {headers}")
    print(f"Total rows (excl. header): {ws.max_row - 1}")

    col_idx = {h: i for i, h in enumerate(headers) if h}
    errors: list[str] = []
    warnings: list[str] = []
    row_data: list[dict[str, str]] = []

    for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if all(v is None for v in row):
            continue

        def val(col_name: str) -> str:
            idx = col_idx.get(col_name)
            if idx is None:
                return ""
            v = row[idx]
            return str(v).strip() if v is not None else ""

        company = val("Company Name")
        country = val("Country")
        city = val("City")
        lead_investor = val("Lead Investor")
        source_url = val("Source URL")
        ann_date = val("Funding Announcement Date")
        pub_date = val("Article Publication Date")
        amount = val("Funding Amount")
        currency = val("Currency")
        stage = val("Funding Round")
        sector = val("Primary Category")

        row_data.append({
            "row": str(row_num),
            "company": company,
            "country": country,
            "city": city,
            "lead_investor": lead_investor,
            "source_url": source_url,
            "ann_date": ann_date,
            "pub_date": pub_date,
            "amount": amount,
            "currency": currency,
            "stage": stage,
            "sector": sector,
        })

        for col in ["Company Name", "Country", "City", "Primary Category", "Lead Investor", "Source URL", "Funding Announcement Date"]:
            if not val(col):
                errors.append(f"Row {row_num} ({company}): BLANK '{col}'")

        if country and country not in ("United States", "India"):
            errors.append(f"Row {row_num} ({company}): Country='{country}' is NOT US or India")

        if ann_date and (ann_date < START_DATE or ann_date > END_DATE):
            errors.append(f"Row {row_num} ({company}): Date '{ann_date}' OUTSIDE window {START_DATE}..{END_DATE}")

        if source_url:
            if any(pat in source_url for pat in SEARCH_PATTERNS):
                errors.append(f"Row {row_num} ({company}): Source URL is a SEARCH PAGE: {source_url}")
            if not source_url.startswith(("http://", "https://")):
                errors.append(f"Row {row_num} ({company}): Invalid URL scheme: {source_url}")

    if check_urls and row_data:
        import requests
        headers_req = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"}
        for rd in row_data:
            u = rd["source_url"]
            if not u:
                continue
            try:
                r = requests.get(u, headers=headers_req, timeout=10)
                if r.status_code >= 400:
                    errors.append(f"Row {rd['row']} ({rd['company']}): Live URL returned HTTP {r.status_code}: {u}")
            except Exception as exc:
                warnings.append(f"Row {rd['row']} ({rd['company']}): Live URL check error ({exc}): {u}")

    print("\n" + "=" * 80)
    print("QUALITY CHECK RESULTS")
    print("=" * 80)
    print(f"Total rows checked: {len(row_data)}")

    if errors:
        print(f"\nFAILED — {len(errors)} error(s) found:\n")
        for e in errors:
            print(f"  ERROR: {e}")
    else:
        print("\nPASSED — Zero errors found.")

    if warnings:
        print(f"\n{len(warnings)} warning(s):")
        for w in warnings:
            print(f"  WARN: {w}")

    print("\n" + "-" * 80)
    print("ALL ROWS:")
    print("-" * 80)
    for rd in row_data:
        print(
            f"  {rd['company'][:24]:<24} | {rd['country'][:13]:<13} | {rd['city'][:13]:<13} "
            f"| {rd['amount'][:12]:<12} {rd['currency']:<3} | {rd['stage'][:10]:<10} "
            f"| {rd['lead_investor'][:22]:<22} | {rd['ann_date']} | {rd['sector']}"
        )
        print(f"    URL: {rd['source_url']}")

    countries: dict[str, int] = {}
    sectors: dict[str, int] = {}
    for rd in row_data:
        countries[rd["country"] or "BLANK"] = countries.get(rd["country"] or "BLANK", 0) + 1
        sectors[rd["sector"] or "BLANK"] = sectors.get(rd["sector"] or "BLANK", 0) + 1

    print("\n" + "=" * 80)
    print("Country distribution:", countries)
    print("Sector distribution :", sectors)
    print("=" * 80)

    return len(errors) == 0 and len(row_data) > 0


if __name__ == "__main__":
    argp = argparse.ArgumentParser()
    argp.add_argument("--check-urls", action="store_true")
    ns = argp.parse_args()
    sys.exit(0 if run_checks(check_urls=ns.check_urls) else 1)
