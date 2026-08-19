"""
Structural heading detector for Mexican regulatory documents.

Detects TÍTULO / CAPÍTULO / SECCIÓN / ARTÍCULO headings and groups the
document text into StructuralBlock objects, each carrying a full ancestry
path (e.g. "TÍTULO PRIMERO > CAPÍTULO I > Artículo 15").

Design decisions:
- Normalization happens only for matching; original text is kept for labels.
- Accents and irregular spacing are stripped before regex comparison so that
  "TÍTULO   PRIMERO", "Titulo Primero" and "TITULO PRIMERO" all match.
- Roman numerals (I, II, IV, XV …) are accepted in article numbers.
- Fallback: if no headings are detected the whole document is returned as a
  single block with structure_path="Documento completo" so unstructured or
  scanned PDFs remain searchable.
"""

import re
import unicodedata
from collections.abc import Iterator

from src.ingest.models import PageText, StructuralBlock

# ---------------------------------------------------------------------------
# Heading patterns — applied on accent-stripped, whitespace-collapsed lines.
# Order: higher-level headings first so the stack logic is unambiguous.
# ---------------------------------------------------------------------------
_HEADING_PATTERNS: list[tuple[int, re.Pattern[str]]] = [
    (1, re.compile(r"^TITULO\s+\S+", re.IGNORECASE)),
    (2, re.compile(r"^CAPITULO\s+\S+", re.IGNORECASE)),
    (3, re.compile(r"^SECCION\s+\d+", re.IGNORECASE)),
    # \b after the number/roman stops partial matches like "VAR" matching "V".
    (4, re.compile(r"^ARTICULO\s+(?:\d+|[IVXLCDM]+)\b\s*[°.]?", re.IGNORECASE)),
]


def _normalize_line(line: str) -> str:
    """Strip accents and collapse whitespace — used only for heading matching."""
    nfd = unicodedata.normalize("NFD", line)
    without_accents = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    return " ".join(without_accents.split())


def _clean_label(original_line: str) -> str:
    """Produce a tidy label from the raw heading line for use in structure_path."""
    return " ".join(original_line.strip().rstrip(".°").split())


def _build_path(stack: list[tuple[int, str]]) -> str:
    return " > ".join(label for _, label in stack)


def _match_heading(normalized: str, original: str) -> tuple[int, str] | None:
    """Return (level, clean_label) if the line is a recognized heading, else None."""
    for level, pattern in _HEADING_PATTERNS:
        if pattern.match(normalized):
            return level, _clean_label(original)
    return None


def _iter_lines(pages: list[PageText]) -> Iterator[tuple[int, str]]:
    """Yield (page_number, line) for every line in document order."""
    for page in pages:
        for line in page.text.splitlines():
            yield page.page_number, line


def detect_structure(pages: list[PageText]) -> list[StructuralBlock]:
    """
    Parse pages into StructuralBlocks bounded by regulatory headings.

    Each block's content is the text that appears after its heading and before
    the next heading of any level.  Text before the first heading is discarded
    (usually cover page / table of contents).
    """
    blocks: list[StructuralBlock] = []
    stack: list[tuple[int, str]] = []  # (level, label) for open ancestors

    current_level: int | None = None
    current_label: str = ""
    current_page: int = 0
    current_lines: list[str] = []

    for page_num, original_line in _iter_lines(pages):
        normalized = _normalize_line(original_line)
        match = _match_heading(normalized, original_line)

        if match is not None:
            level, label = match

            # Close the block that was open before this heading.
            if current_level is not None:
                blocks.append(
                    StructuralBlock(
                        level=current_level,
                        label=current_label,
                        content="\n".join(current_lines).strip(),
                        page_number=current_page,
                        # Path is built from the stack as it stands *before* we
                        # push the new heading — it already contains the current
                        # block's own label from when it was opened.
                        structure_path=_build_path(stack),
                    )
                )

            # Update ancestry stack: pop siblings and descendants, push self.
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, label))

            current_level = level
            current_label = label
            current_page = page_num
            current_lines = []
        else:
            if current_level is not None:
                current_lines.append(original_line)
            # Lines before the first heading (e.g. cover page) are ignored.

    # Close the final open block.
    if current_level is not None:
        blocks.append(
            StructuralBlock(
                level=current_level,
                label=current_label,
                content="\n".join(current_lines).strip(),
                page_number=current_page,
                structure_path=_build_path(stack),
            )
        )

    if not blocks:
        # Fallback: no headings found — treat the entire document as one block.
        all_text = "\n".join(line for _, line in _iter_lines(pages)).strip()
        first_page = pages[0].page_number if pages else 1
        return [
            StructuralBlock(
                level=0,
                label="Documento completo",
                content=all_text,
                page_number=first_page,
                structure_path="Documento completo",
            )
        ]

    return blocks
