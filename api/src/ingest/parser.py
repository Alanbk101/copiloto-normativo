from pathlib import Path

import pdfplumber

from src.ingest.models import PageText


def extract_pages(pdf_path: Path) -> list[PageText]:
    """
    Extract text per page from a PDF file.

    Pages with no selectable text (e.g. scanned images without OCR) return an
    empty string rather than raising — the caller decides how to handle blanks.
    """
    pages: list[PageText] = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append(PageText(page_number=i, text=text))
    return pages
