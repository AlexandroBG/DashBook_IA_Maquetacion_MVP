"""
core/extractor.py — Extracción de texto crudo desde el manuscrito original.

Soporta PDF, DOCX, TXT y Markdown. La salida siempre es texto plano con
saltos de párrafo normalizados (`\n\n` entre párrafos); el detalle de
qué es un capítulo se resuelve después, en core/structure_detector.py.
"""

from __future__ import annotations

from pathlib import Path

import docx
import pymupdf as fitz  # PyMuPDF (el paquete se sigue instalando como PyMuPDF)

from config import SUPPORTED_INPUT_EXTENSIONS
from core.errors import PipelineError
from models.book import InputFormat, Manuscript
from utils.logging import get_logger

logger = get_logger(__name__)

_EXT_TO_FORMAT = {
    ".pdf": InputFormat.PDF,
    ".docx": InputFormat.DOCX,
    ".txt": InputFormat.TXT,
    ".md": InputFormat.MD,
    ".markdown": InputFormat.MD,
}


def extract_manuscript(file_path: str | Path) -> Manuscript:
    """Punto de entrada único: detecta el formato por extensión y despacha."""
    path = Path(file_path)
    if not path.exists():
        raise PipelineError(f"No se encontró el archivo: {path}")

    ext = path.suffix.lower()
    if ext not in SUPPORTED_INPUT_EXTENSIONS:
        raise PipelineError(
            f"Formato '{ext}' no soportado. Formatos válidos: "
            f"{', '.join(sorted(SUPPORTED_INPUT_EXTENSIONS))}"
        )

    logger.info("Extrayendo texto de %s (%s)", path.name, ext)

    if ext == ".pdf":
        raw_text = _extract_pdf(path)
    elif ext == ".docx":
        raw_text = _extract_docx(path)
    else:  # .txt, .md, .markdown
        raw_text = _extract_plain(path)

    if not raw_text or not raw_text.strip():
        raise PipelineError(
            "El manuscrito no contiene texto extraíble. Si es un PDF "
            "escaneado (imágenes), necesita pasar por OCR primero."
        )

    return Manuscript(source_format=_EXT_TO_FORMAT[ext], raw_text=raw_text)


def _extract_pdf(path: Path) -> str:
    """Extrae texto de un PDF preservando párrafos por bloque de texto.

    Usamos el modo "blocks" de PyMuPDF en lugar de una extracción plana
    porque conserva mejor los saltos de párrafo reales frente a los
    saltos de línea artificiales de la justificación del PDF original.
    """
    paragraphs: list[str] = []
    with fitz.open(path) as doc:
        for page in doc:
            blocks = page.get_text("blocks")
            # blocks: (x0, y0, x1, y1, text, block_no, block_type)
            blocks_sorted = sorted(blocks, key=lambda b: (round(b[1], 1), b[0]))
            for b in blocks_sorted:
                text = b[4].strip()
                if not text:
                    continue
                # Une líneas partidas dentro del mismo bloque en una sola
                # línea de párrafo; conserva dobles saltos si ya existían
                # (p. ej. poesía o listas).
                joined = " ".join(line.strip() for line in text.splitlines() if line.strip())
                paragraphs.append(joined)
    return "\n\n".join(paragraphs)


def _extract_docx(path: Path) -> str:
    """Extrae texto de un DOCX, un párrafo de Word = un párrafo de salida."""
    document = docx.Document(str(path))
    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def _extract_plain(path: Path) -> str:
    """Lee TXT/MD tal cual, normalizando finales de línea."""
    raw = path.read_text(encoding="utf-8", errors="replace")
    return raw.replace("\r\n", "\n").replace("\r", "\n")
