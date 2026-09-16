"""
ai/front_matter.py — Genera las páginas preliminares del libro
(portadilla, portada, página de copyright, dedicatoria) con IA, en el
idioma del manuscrito.

Importante: la IA redacta texto (copyright, dedicatoria genérica si no
se proporciona una), pero JAMÁS decide números de página, saltos de
página ni maquetación — eso es responsabilidad exclusiva de
layout/engine.py, que solo consume los campos de FrontMatter como texto.

Este módulo no conoce el proveedor de IA concreto: solo pide una
respuesta JSON a través de ai.client.
"""

from __future__ import annotations

from ai.client import generate_json
from config import SUPPORTED_LANGUAGES
from models.book import BookMetadata, FrontMatter
from utils.logging import get_logger

logger = get_logger(__name__)

_REQUIRED_FIELDS = {"half_title", "title_page_title", "title_page_author", "copyright_block"}

_PROMPT_TEMPLATE = """Eres un editor profesional preparando las páginas \
preliminares (front matter) de un libro para imprenta. Escribe TODO el \
contenido en {language_name}, con el registro formal habitual de una \
editorial.

Datos del libro:
- Título: {title}
- Subtítulo: {subtitle}
- Autor/a: {author}
- Editorial: {publisher}
- Año de publicación: {year}
- ISBN: {isbn}
{dedication_instruction}

Genera EXCLUSIVAMENTE un JSON con esta forma exacta, sin texto adicional \
ni backticks de Markdown:
{{
  "half_title": "solo el título, tal cual debe verse en la portadilla",
  "title_page_title": "título para la página de portada",
  "title_page_subtitle": "subtítulo o null si no hay",
  "title_page_author": "nombre del autor tal cual debe figurar",
  "copyright_block": "texto legal de copyright, con saltos de línea \\n \
donde corresponda: © año Autor, editorial, aviso de reservados todos \
los derechos, y si hay ISBN inclúyelo. 5-8 líneas, sobrio, sin adornos.",
  "dedication": "texto breve de dedicatoria o null si no corresponde"
}}
"""


def generate_front_matter(metadata: BookMetadata, dedication_hint: str | None = None) -> FrontMatter:
    lang_meta = SUPPORTED_LANGUAGES[metadata.language]
    dedication_instruction = (
        f"- Dedicatoria deseada por el autor (adáptala/púlela): {dedication_hint}"
        if dedication_hint
        else "- No se proporcionó dedicatoria: devuelve null en ese campo."
    )

    prompt = _PROMPT_TEMPLATE.format(
        language_name=lang_meta["name"],
        title=metadata.title,
        subtitle=metadata.subtitle or "(sin subtítulo)",
        author=metadata.author,
        publisher=metadata.publisher,
        year=metadata.year,
        isbn=metadata.isbn or "(sin ISBN asignado todavía)",
        dedication_instruction=dedication_instruction,
    )

    logger.info("Generando front matter con IA (idioma=%s)", metadata.language)
    data = generate_json(prompt, required_fields=_REQUIRED_FIELDS)

    return FrontMatter(
        half_title=data["half_title"],
        title_page_title=data["title_page_title"],
        title_page_subtitle=data.get("title_page_subtitle") or None,
        title_page_author=data["title_page_author"],
        copyright_block=data["copyright_block"],
        dedication=data.get("dedication") or None,
    )
