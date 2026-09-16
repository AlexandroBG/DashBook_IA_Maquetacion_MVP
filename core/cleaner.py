"""
core/cleaner.py — Limpieza y normalización tipográfica del texto extraído.

Esto es lo que separa un PDF "generado por script" de uno con pinta
editorial real: comillas correctas por idioma, espacios insecables donde
la tipografía francesa los exige, guiones largos para diálogo, eliminación
de artefactos de la extracción (guiones de corte de línea del PDF
original, espacios múltiples, saltos de página sueltos).

Todo esto ocurre ANTES de que el texto llegue a la IA o al motor de
composición, para que ambos trabajen sobre texto ya limpio.
"""

from __future__ import annotations

import re
import unicodedata

from config import SUPPORTED_LANGUAGES
from core.errors import PipelineError
from utils.logging import get_logger

logger = get_logger(__name__)

NBSP = "\u00A0"
NNBSP = "\u202F"  # espacio fino insecable, el correcto para tipografía francesa

_STRAIGHT_DOUBLE = re.compile(r'"([^"]*)"')
_STRAIGHT_SINGLE = re.compile(r"'([^']*)'")

# Guion de corte de línea heredado de la maquetación del PDF original,
# p. ej. "informa-\nción" -> "información". Solo se une si lo que sigue
# empieza en minúscula (evita destruir listas con guiones reales).
_LINE_BREAK_HYPHEN = re.compile(r"(\w)-\n(\w)")

_MULTI_SPACE = re.compile(r"[ \t]{2,}")
_MULTI_BLANK_LINES = re.compile(r"\n{3,}")


def normalize_manuscript_text(raw_text: str, language: str) -> str:
    """Aplica toda la cadena de limpieza y devuelve texto listo para
    detección de estructura y composición.
    """
    if language not in SUPPORTED_LANGUAGES:
        raise PipelineError(f"Idioma no soportado en cleaner: {language}")

    text = raw_text
    text = _normalize_unicode(text)
    text = _fix_hyphenated_linebreaks(text)
    text = _collapse_whitespace(text)
    text = _normalize_dashes(text)
    text = _apply_quote_style(text, language)
    if SUPPORTED_LANGUAGES[language]["quote_style"] == "guillemets_nbsp":
        text = _apply_french_spacing(text)

    logger.info("Texto normalizado: %d caracteres (idioma=%s)", len(text), language)
    return text.strip() + "\n"


def _normalize_unicode(text: str) -> str:
    """NFC: evita que letras acentuadas queden como base+diacrítico
    combinante, lo que rompería el guionado y la búsqueda de patrones.
    """
    return unicodedata.normalize("NFC", text)


def _fix_hyphenated_linebreaks(text: str) -> str:
    return _LINE_BREAK_HYPHEN.sub(r"\1\2", text)


def _collapse_whitespace(text: str) -> str:
    text = _MULTI_SPACE.sub(" ", text)
    text = _MULTI_BLANK_LINES.sub("\n\n", text)
    return text


def _normalize_dashes(text: str) -> str:
    """Convierte guiones de diálogo "--" o "-" sueltos a raya (—),
    estándar en narrativa en los cinco idiomas soportados.
    """
    text = re.sub(r"(?<!\w)--(?!\w)", "—", text)
    # Guion al inicio de línea usado como marcador de diálogo -> raya.
    text = re.sub(r"(?m)^-(?=\s*\S)", "—", text)
    return text


def _apply_quote_style(text: str, language: str) -> str:
    style = SUPPORTED_LANGUAGES[language]["quote_style"]
    if style in ("guillemets", "guillemets_nbsp"):
        text = _STRAIGHT_DOUBLE.sub(r"«\1»", text)
    else:  # curly (inglés)
        text = _STRAIGHT_DOUBLE.sub(r"“\1”", text)
    text = _STRAIGHT_SINGLE.sub(r"‘\1’", text)
    return text


def _apply_french_spacing(text: str) -> str:
    """Espacio fino insecable antes de ; : ! ? y dentro de « » — regla
    tipográfica francesa estándar (Imprimerie Nationale).
    """
    text = re.sub(r"«\s*", f"«{NNBSP}", text)
    text = re.sub(r"\s*»", f"{NNBSP}»", text)
    text = re.sub(r"\s*([;:!?])", rf"{NNBSP}\1", text)
    # El "?" doble tras apertura de interrogación no debe generar doble nbsp.
    text = text.replace(f"{NNBSP}{NNBSP}", NNBSP)
    return text
