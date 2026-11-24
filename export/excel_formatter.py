"""
export/excel_formatter.py
=========================
Generates professionally formatted, multi-sheet Excel workbooks using openpyxl.

Sheets generated:
1. 'Funding Announcements' (Main consolidated sheet)
2. 'Companies' (Deduplicated company profiles)
3. 'Funding Rounds' (Detailed rounds breakdown)
4. 'Source Articles' (Article provenance and traceability)
5. 'Records Requiring Review' (Candidates flagged for manual human audit)

Formatting features:
- Clean styling with dark navy headers, white bold font.
- Auto-adjusted column widths.
- Currency and date number formatting.
- Thin borders and alternating row readability.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

# Colors & Styling
_HEADER_FILL = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
_HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
_THIN_BORDER = Border(
    left=Side(style="thin", color="D9D9D9"),
    right=Side(style="thin", color="D9D9D9"),
    top=Side(style="thin", color="D9D9D9"),
    bottom=Side(style="thin", color="D9D9D9"),
)
_ZEBRA_FILL = PatternFill(start_color="F9FAFB", end_color="F9FAFB", fill_type="solid")


def apply_table_formatting(ws: openpyxl.worksheet.worksheet.Worksheet) -> None:
    """Format headers, borders, zebra striping, and column widths."""
    # Format header row
    for col_idx in range(1, ws.max_column + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Format data rows
    for row_idx in range(2, ws.max_row + 1):
        is_even = row_idx % 2 == 0
        for col_idx in range(1, ws.max_column + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.border = _THIN_BORDER
            if is_even:
                cell.fill = _ZEBRA_FILL

    # Auto-adjust column widths (bounded between 12 and 55 characters)
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = max(12, min(max_len + 3, 55))


def create_excel_workbook(
    main_rows: list[dict[str, Any]],
    company_rows: list[dict[str, Any]],
    round_rows: list[dict[str, Any]],
    article_rows: list[dict[str, Any]],
    review_rows: list[dict[str, Any]],
    output_path: Path,
) -> Path:
    """
    Build and save the 5-sheet workbook.
    """
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    def _write_sheet(title: str, rows: list[dict[str, Any]], columns: list[str]) -> None:
        ws = wb.create_sheet(title=title)
        ws.append(columns)
        for r in rows:
            ws.append([r.get(c, "") for c in columns])
        apply_table_formatting(ws)

    # 1. Main Sheet: Funding Announcements
    main_cols = [
        "Company Name", "Country", "City", "Website", "Company Description",
        "Primary Category", "Secondary Categories", "Relevance Status",
        "Funding Amount", "Currency", "Funding Round", "Funding Announcement Date",
        "Article Publication Date", "Lead Investor", "Investors", "Source Name",
        "Source URL", "Verification Status"
    ]
    _write_sheet("Funding Announcements", main_rows, main_cols)

    # 2. Companies Sheet
    comp_cols = [
        "Company Name", "Country", "City", "Website", "Primary Category",
        "Secondary Categories", "Relevance Status", "Confidence Score", "Description"
    ]
    _write_sheet("Companies", company_rows, comp_cols)

    # 3. Funding Rounds Sheet
    round_cols = [
        "Company Name", "Funding Round", "Funding Amount", "Currency",
        "Original Amount Text", "Announcement Date", "Lead Investor", "Investors"
    ]
    _write_sheet("Funding Rounds", round_rows, round_cols)

    # 4. Source Articles Sheet
    art_cols = [
        "Article Title", "Source Name", "Source URL", "Published Date", "Extraction Status"
    ]
    _write_sheet("Source Articles", article_rows, art_cols)

    # 5. Records Requiring Review Sheet
    rev_cols = [
        "Company Name", "Country", "City", "Primary Category", "Relevance Status",
        "Funding Amount", "Funding Round", "Review Reason", "Source URL"
    ]
    _write_sheet("Records Requiring Review", review_rows, rev_cols)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output_path)
    logger.info("Formatted Excel workbook saved to %s", output_path)
    return output_path
