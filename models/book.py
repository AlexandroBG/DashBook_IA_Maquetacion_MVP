"""
models/book.py — Modelos de datos (Pydantic) que atraviesan todo el
pipeline: del manuscrito crudo al libro maquetado.

Mantener estos modelos como la única fuente de verdad evita que cada
módulo invente su propio diccionario ad-hoc para pasar datos al siguiente.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class InputFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MD = "md"


class ChapterBreakType(str, Enum):
    """Cómo debe romper la página el elemento estructural."""

    PART = "part"  # "Parte I" — siempre página impar, con página en blanco si hace falta
    CHAPTER = "chapter"  # "Capítulo 1" — siempre página impar (recto)
    SECTION = "section"  # subdivisión interna, sin salto de página forzado


class Chapter(BaseModel):
    """Una unidad estructural del manuscrito (parte, capítulo o sección)."""

    order: int
    title: str
    break_type: ChapterBreakType = ChapterBreakType.CHAPTER
    # El contenido se guarda ya como HTML (párrafos <p>) para que el
    # motor de composición no tenga que volver a interpretar Markdown.
    html_content: str
    detected_by: str = "heuristic"  # "heuristic" | "ai"

    @field_validator("title")
    @classmethod
    def _strip_title(cls, v: str) -> str:
        return v.strip()


class FrontMatter(BaseModel):
    """Páginas preliminares generadas por IA (en el idioma del manuscrito)."""

    half_title: str  # portadilla: solo el título
    title_page_title: str
    title_page_subtitle: Optional[str] = None
    title_page_author: str
    copyright_block: str  # texto legal completo, ya formateado en líneas
    dedication: Optional[str] = None


class BookMetadata(BaseModel):
    """Metadatos editoriales que el usuario introduce o confirma."""

    title: str
    subtitle: Optional[str] = None
    author: str
    language: str = Field(description="Código ISO 639-1: es, ca, fr, it, en")
    publisher: str = "DashBook"
    isbn: Optional[str] = None
    year: int
    trim_size: str = "6x9"
    include_toc: bool = True
    # Género/tipo de libro (novela, poesía, ensayo, infantil...). Es
    # informativo: hoy solo lo usa ai/kdp_metadata.py para adaptar el
    # tono de la sinopsis comercial; no afecta a la maquetación.
    genre: Optional[str] = None

    @field_validator("language")
    @classmethod
    def _validate_language(cls, v: str) -> str:
        from config import SUPPORTED_LANGUAGES

        if v not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Idioma '{v}' no soportado. Debe ser uno de: {', '.join(SUPPORTED_LANGUAGES)}"
            )
        return v


class KDPMetadata(BaseModel):
    """Metadatos comerciales para la ficha de venta (KDP u otra tienda).

    Generados por IA a partir del manuscrito ya maquetado — nunca se
    usan en la composición del PDF, son "front matter hacia afuera":
    lo que ve un lector en la tienda, no en el libro.
    """

    back_cover_blurb: str  # sinopsis de contraportada, 80-150 palabras
    keywords: list[str] = Field(default_factory=list)  # 5-7 palabras clave de descubribilidad
    categories: list[str] = Field(default_factory=list)  # 2-3 categorías/género tipo BISAC



class LayoutSpec(BaseModel):
    """Especificación física de página, resuelta a partir de layout/kdp_rules.py."""

    trim_width_in: float
    trim_height_in: float
    margin_top_in: float
    margin_bottom_in: float
    margin_outside_in: float
    margin_gutter_in: float  # margen interior/lomo, calculado según nº de páginas
    orphans: int
    widows: int


class Manuscript(BaseModel):
    """Resultado de core/extractor.py + core/cleaner.py: texto crudo ya normalizado."""

    source_format: InputFormat
    raw_text: str
    detected_language: Optional[str] = None
    char_count: int = 0

    def model_post_init(self, __context) -> None:
        # Se recalcula siempre a partir de raw_text (también tras
        # reasignar raw_text manualmente, p. ej. después de limpiar el
        # texto en cleaner.py), en vez de depender de que quien
        # construye el modelo pase char_count a mano.
        object.__setattr__(self, "char_count", len(self.raw_text))


class BookProject(BaseModel):
    """Estado completo de un proyecto de maquetación, de punta a punta."""

    metadata: BookMetadata
    manuscript: Optional[Manuscript] = None
    chapters: list[Chapter] = Field(default_factory=list)
    front_matter: Optional[FrontMatter] = None
    layout_spec: Optional[LayoutSpec] = None
    output_pdf_path: Optional[str] = None
    estimated_page_count: Optional[int] = None
    # Extensiones de IA opcionales (ver ai/kdp_metadata.py y
    # ai/quality_check.py): nunca bloquean la generación del PDF si
    # fallan — el libro se compone igual aunque estas dos falten.
    kdp_metadata: Optional[KDPMetadata] = None
    quality_warnings: list[str] = Field(default_factory=list)
