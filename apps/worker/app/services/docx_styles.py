"""
DOCX Styles — shared constants for the DOCX builder.

Colors, fonts, and type labels used by cover pages and headings.
"""

from docx.shared import RGBColor

HEADING_COLOR_1 = RGBColor(0x1A, 0x1A, 0x2E)
HEADING_COLOR_2 = RGBColor(0x2D, 0x5B, 0x9E)
MUTED_COLOR = RGBColor(0x99, 0x99, 0x99)
FONT_NAME = "Calibri"

TYPE_LABELS: dict[str, str] = {
    "executive_summary": "EXECUTIVE SUMMARY",
    "investment_memo": "INVESTMENT MEMO",
    "dd_report": "RAPPORT DE DUE DILIGENCE",
}
