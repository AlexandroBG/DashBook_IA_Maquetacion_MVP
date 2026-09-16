"""
core/structure_detector.py — Detecta la estructura de capítulos/partes del
manuscrito.

Estrategia en dos fases (nunca se le pide a la IA que inserte saltos de
página: eso lo decide siempre el CSS en layout/engine.py):

1. Heurística por patrones: cubre el 90%+ de manuscritos reales, donde
   los capítulos están marcados de forma razonablemente estándar
   ("Capítulo 1", "Chapter One", una línea corta en mayúsculas, etc.).
2. Fallback con IA SOLO si la heurística no encuentra ninguna división
   de capítulos: se le pide al modelo que devuelva, en JSON
   estructurado, los títulos de capítulo que reconozca en el texto,
   NUNCA que reescriba o resuma el contenido.

Este módulo no sabe qué proveedor de IA está detrás de `ai.client`
(Gemini, u otro en el futuro) — solo pide una respuesta JSON.
"""

from __future__ import annotations

import html
import re

from ai.client import generate_json
from config import (
    MAX_CHAPTER_DETECTION_CHARS_FOR_LLM,
    SUPPORTED_LANGUAGES,
)
from core.errors import AIProviderError, PipelineError
from models.book import Chapter, ChapterBreakType
from utils.logging import get_logger

logger = get_logger(__name__)


def detect_chapters(raw_text: str, language: str) -> list[Chapter]:
    """Punto de entrada: intenta heurística, si falla usa la IA."""
    chapters = _detect_by_heuristic(raw_text, language)
    if chapters:
        logger.info("Estructura detectada por heurística: %d capítulos", len(chapters))
        return chapters

    logger.info("Heurística sin resultados; usando fallback con IA")
    chapters = _detect_by_ai(raw_text, language)
    if not chapters:
        raise PipelineError(
            "No fue posible detectar la estructura de capítulos del "
            "manuscrito, ni por patrones ni con IA. Revisa que el "
            "manuscrito use algún marcador de capítulo reconocible."
        )
    logger.info("Estructura detectada por IA: %d capítulos", len(chapters))
    return chapters


# ---------------------------------------------------------------------------
# Fase 1: heurística por patrones
# ---------------------------------------------------------------------------


def _build_marker_pattern(language: str) -> re.Pattern:
    words = SUPPORTED_LANGUAGES[language]["chapter_markers"]
    word_alt = "|".join(re.escape(w) for w in words)
    # Coincide con inicio de línea + palabra marcadora + número/romano opcional
    # + título opcional en la misma línea. Insensible a mayúsculas.
    pattern = rf"(?im)^\s*(?:{word_alt})\s*([0-9IVXLCDM]+)?\.?\s*[:\-—]?\s*(.*)$"
    return re.compile(pattern)


def _detect_by_heuristic(raw_text: str, language: str) -> list[Chapter]:
    pattern = _build_marker_pattern(language)
    paragraphs = raw_text.split("\n\n")

    matches: list[tuple[int, str]] = []  # (índice de párrafo, título completo)
    for idx, para in enumerate(paragraphs):
        first_line = para.strip().splitlines()[0] if para.strip() else ""
        if not first_line or len(first_line) > 80:
            continue  # una línea de capítulo nunca es un párrafo largo
        m = pattern.match(first_line)
        if m:
            matches.append((idx, first_line.strip()))
            continue
        # También aceptamos líneas cortas todo en mayúsculas como título
        # de capítulo (convención común en manuscritos sin numeración
        # explícita), evitando falsos positivos con siglas sueltas.
        if _looks_like_allcaps_title(first_line):
            matches.append((idx, first_line.strip()))

    if len(matches) < 2:
        # Un único "capítulo" detectado no es una estructura fiable;
        # mejor delegar en la IA que arriesgarse a una maquetación mal
        # segmentada.
        return []

    return _build_chapters_from_matches(paragraphs, matches)


def _looks_like_allcaps_title(line: str) -> bool:
    letters = [c for c in line if c.isalpha()]
    if len(letters) < 3 or len(line) > 60:
        return False
    return all(c.isupper() for c in letters)


def _build_chapters_from_matches(
    paragraphs: list[str], matches: list[tuple[int, str]]
) -> list[Chapter]:
    chapters: list[Chapter] = []
    for order, (start_idx, title) in enumerate(matches, start=1):
        end_idx = matches[order][0] if order < len(matches) else len(paragraphs)
        body_paragraphs = paragraphs[start_idx + 1 : end_idx]
        html_content = _paragraphs_to_html(body_paragraphs)
        chapters.append(
            Chapter(
                order=order,
                title=title or f"Capítulo {order}",
                break_type=ChapterBreakType.CHAPTER,
                html_content=html_content,
                detected_by="heuristic",
            )
        )
    return chapters


def _paragraphs_to_html(paragraphs: list[str]) -> str:
    parts = []
    for para in paragraphs:
        text = para.strip()
        if not text:
            continue
        escaped = html.escape(text).replace("\n", "<br/>")
        parts.append(f"<p>{escaped}</p>")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Fase 2: fallback con IA
# ---------------------------------------------------------------------------

_AI_PROMPT_TEMPLATE = """Eres un asistente editorial. Tu única tarea es \
identificar los títulos de capítulo EXACTOS (tal cual aparecen, palabra \
por palabra) dentro del manuscrito que te paso, en el idioma indicado. \
No inventes títulos, no resumas, no traduzcas, no corrijas ortografía. \
Si el manuscrito no tiene divisiones de capítulo claras, devuelve una \
lista vacía. Responde EXCLUSIVAMENTE con un JSON con esta forma exacta, \
sin texto adicional ni backticks de Markdown:
{{"chapter_titles": ["título exacto 1", "título exacto 2", ...]}}

Idioma del manuscrito: {language_name}

--- MANUSCRITO (posible extracto) ---
{text_sample}
"""


def _detect_by_ai(raw_text: str, language: str) -> list[Chapter]:
    sample = raw_text[:MAX_CHAPTER_DETECTION_CHARS_FOR_LLM]
    titles = _call_ai_for_titles(sample, language)
    if len(titles) < 2:
        return []

    # Localizamos cada título literal dentro del texto completo para
    # partir el manuscrito por posiciones reales, no por lo que "cree"
    # la IA que hay entre medias (así la IA nunca toca el contenido).
    positions: list[tuple[int, str]] = []
    for title in titles:
        idx = raw_text.find(title)
        if idx == -1:
            logger.warning("Título devuelto por la IA no se encontró literal: %r", title)
            continue
        positions.append((idx, title))

    if len(positions) < 2:
        return []

    positions.sort(key=lambda p: p[0])
    chapters: list[Chapter] = []
    for order, (start, title) in enumerate(positions, start=1):
        end = positions[order][0] if order < len(positions) else len(raw_text)
        body = raw_text[start + len(title) : end]
        paragraphs = [p for p in body.split("\n\n") if p.strip()]
        chapters.append(
            Chapter(
                order=order,
                title=title,
                break_type=ChapterBreakType.CHAPTER,
                html_content=_paragraphs_to_html(paragraphs),
                detected_by="ai",
            )
        )
    return chapters


def _call_ai_for_titles(text_sample: str, language: str) -> list[str]:
    lang_name = SUPPORTED_LANGUAGES[language]["name"]
    prompt = _AI_PROMPT_TEMPLATE.format(language_name=lang_name, text_sample=text_sample)

    data = generate_json(prompt, required_fields={"chapter_titles"})
    titles = data.get("chapter_titles", [])
    if not isinstance(titles, list):
        raise AIProviderError("Formato inesperado en la respuesta del proveedor de IA")
    return [str(t).strip() for t in titles if str(t).strip()]
