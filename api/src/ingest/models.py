from dataclasses import dataclass


@dataclass
class PageText:
    page_number: int  # 1-indexed
    text: str


@dataclass
class StructuralBlock:
    level: int           # 1=Título, 2=Capítulo, 3=Sección, 4=Artículo, 0=fallback
    label: str           # heading text, e.g. "Artículo 15"
    content: str         # body text under this heading
    page_number: int     # page where the heading appears
    structure_path: str  # e.g. "TÍTULO PRIMERO > CAPÍTULO I > Artículo 15"


@dataclass
class Chunk:
    content: str
    structure_path: str
    page_number: int
    chunk_index: int  # 0-indexed position across the full document
