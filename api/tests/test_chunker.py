"""
Tests for the ingest pipeline: structure detection + chunking.

No PDF fixture needed — all tests operate on inline text, exercising
detect_structure and chunk_document independently of the parser.
"""

import pytest

from src.ingest.chunker import chunk_document
from src.ingest.models import PageText
from src.ingest.structure import detect_structure

# ---------------------------------------------------------------------------
# Fixtures & sample data
# ---------------------------------------------------------------------------

# Repeat enough times to exceed the 4 000-char sub-chunk threshold.
_LONG_CONTENT = (
    "Este artículo contiene disposiciones muy extensas sobre la materia regulatoria. " * 60
)

SAMPLE_TEXT = f"""TÍTULO PRIMERO
De las Disposiciones Generales

CAPÍTULO I
Objeto y Ámbito de Aplicación

Artículo 1.
El presente Reglamento tiene por objeto establecer las disposiciones generales.

Artículo 2.
Para los efectos de este Reglamento se entenderá por:
I. Autoridad: la dependencia encargada de aplicar el presente ordenamiento;
II. Reglamento: el presente instrumento normativo.

CAPÍTULO II
De los Sujetos Obligados

Artículo 3.
{_LONG_CONTENT}"""

# Heading lines with irregular whitespace — simulates noisy PDF extraction.
_DIRTY_TEXT = """
  TÍTULO   PRIMERO
De las disposiciones generales

  Artículo   1 .
Texto del artículo con encabezado mal espaciado pero que debe detectarse.
"""


@pytest.fixture
def sample_chunks():
    pages = [PageText(page_number=1, text=SAMPLE_TEXT)]
    blocks = detect_structure(pages)
    return chunk_document(blocks)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_articulo_limites(sample_chunks):
    """Each short artículo becomes exactly one chunk."""
    art1 = [c for c in sample_chunks if c.structure_path.endswith("Artículo 1")]
    art2 = [c for c in sample_chunks if c.structure_path.endswith("Artículo 2")]
    assert len(art1) == 1
    assert len(art2) == 1


def test_structure_path_correcto(sample_chunks):
    """structure_path includes the full heading ancestry, in order."""
    art2 = [c for c in sample_chunks if c.structure_path.endswith("Artículo 2")]
    assert art2[0].structure_path == "TÍTULO PRIMERO > CAPÍTULO I > Artículo 2"


def test_articulo_largo_se_parte(sample_chunks):
    """An artículo whose content exceeds MAX_CHARS is split into multiple chunks."""
    art3 = [c for c in sample_chunks if "Artículo 3" in c.structure_path]
    assert len(art3) > 1, "Artículo 3 debe producir más de un chunk por ser largo"


def test_sub_chunks_heredan_path(sample_chunks):
    """All sub-chunks of a split artículo share the same structure_path."""
    art3 = [c for c in sample_chunks if "Artículo 3" in c.structure_path]
    expected = "TÍTULO PRIMERO > CAPÍTULO II > Artículo 3"
    assert all(c.structure_path == expected for c in art3)


def test_chunk_indices_consecutivos(sample_chunks):
    """chunk_index values form a gapless sequence starting at 0."""
    indices = [c.chunk_index for c in sample_chunks]
    assert indices == list(range(len(sample_chunks)))


def test_dirty_text_heading_detection():
    """
    Headings with extra leading spaces and collapsed interior spaces must still
    be detected. Documents this guarantee so regressions are caught early.
    """
    pages = [PageText(page_number=1, text=_DIRTY_TEXT)]
    blocks = detect_structure(pages)
    chunks = chunk_document(blocks)

    art1 = [c for c in chunks if "Artículo 1" in c.structure_path]
    assert len(art1) == 1, (
        "Debe detectar 'Artículo 1' aunque el encabezado tenga espacios irregulares"
    )
    assert "TÍTULO PRIMERO" in art1[0].structure_path


def test_fallback_sin_estructura():
    """
    When no headings are found the whole document is returned as a single chunk
    with structure_path='Documento completo', keeping it searchable.
    """
    pages = [PageText(page_number=1, text="Texto sin encabezados.\n\nOtro párrafo.")]
    blocks = detect_structure(pages)
    assert len(blocks) == 1
    assert blocks[0].structure_path == "Documento completo"
    assert "Texto sin encabezados" in blocks[0].content
