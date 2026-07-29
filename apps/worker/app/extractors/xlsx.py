"""
XLSX/CSV extractor — uses openpyxl + pandas for spreadsheet extraction.
Converts each sheet to a readable text table format.
"""

import logging

import pandas as pd

from . import ExtractionResult

logger = logging.getLogger(__name__)

# Limit rows to prevent memory issues on huge spreadsheets
MAX_ROWS_PER_SHEET = 5000


async def extract_xlsx(file_path: str, file_type: str = "xlsx") -> ExtractionResult:
    """Extract text from an XLSX or CSV file."""
    sheets: list[str] = []

    if file_type == "csv":
        df = pd.read_csv(file_path, nrows=MAX_ROWS_PER_SHEET)
        sheet_text = _dataframe_to_text(df, "Data")
        sheets.append(sheet_text)
    else:
        xls = pd.ExcelFile(file_path, engine="openpyxl")
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name, nrows=MAX_ROWS_PER_SHEET)
            if df.empty:
                continue
            sheet_text = _dataframe_to_text(df, sheet_name)
            sheets.append(sheet_text)

    full_text = "\n\n".join(sheets)
    word_count = len(full_text.split())
    page_count = len(sheets) or 1

    logger.info(
        f"{'CSV' if file_type == 'csv' else 'XLSX'} extracted: "
        f"{page_count} sheets, {word_count} words — {file_path}"
    )

    return ExtractionResult(
        text=full_text,
        page_count=page_count,
        word_count=word_count,
        metadata={
            "extractor": "pandas",
            "sheet_count": page_count,
        },
    )


def _dataframe_to_text(df: pd.DataFrame, sheet_name: str) -> str:
    """Convert a DataFrame to a readable text format with headers."""
    lines = [f"## Sheet: {sheet_name}"]
    lines.append(f"Rows: {len(df)}, Columns: {len(df.columns)}")
    lines.append("")

    # Column headers
    headers = [str(col) for col in df.columns]
    lines.append(" | ".join(headers))
    lines.append(" | ".join(["---"] * len(headers)))

    # Data rows
    for _, row in df.iterrows():
        values = [str(v) if pd.notna(v) else "" for v in row]
        lines.append(" | ".join(values))

    return "\n".join(lines)
