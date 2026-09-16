"""
ai/kdp_metadata.py — Genera los metadatos comerciales de la ficha de
venta (sinopsis de contraportada, palabras clave, categorías), en el
idioma del manuscrito.

Esto es una extensión natural del mismo rol que ya tiene la IA en el
proyecto (ai/front_matter.py): redactar texto editorial a partir de
metadatos, nunca decidir maquetación. La diferencia es que
KDPMetadata no forma parte del PDF — es lo que ve un lector en la
tienda (KDP, web de la editorial...), no dentro del libro.

Paso OPCIONAL del pipeline: si falla (cuota, red, JSON inválido), el
libro se compone igual — ver core/book_builder.py, que atrapa
AIProviderError en esta llamada y continúa sin bloquear el PDF.
"""

from __future__ import annotations

from ai.client import generate_json
from config import SUPPORTED_LANGUAGES
from models.book import BookMetadata, Chapter, KDPMetadata
from utils.logging import get_logger

logger = get_logger(__name__)

_REQUIRED_FIELDS = {"back_cover_blurb", "keywords", "categories"}

_PROMPT_TEMPLATE = """Eres un editor comercial preparando la ficha de venta \
de un libro (el texto que un lector ve en la tienda, NO dentro del \
libro). Escribe TODO el contenido en {language_name}.

Datos del libro:
- Título: {title}
- Subtítulo: {subtitle}
- Autor/a: {author}
- Género/tipo de libro: {genre}

Primeras palabras del manuscrito, para que captes tono y género real \
(no las cites literalmente, son solo contexto):
---
{excerpt}
---

Genera EXCLUSIVAMENTE un JSON con esta forma exacta, sin texto adicional \
ni backticks de Markdown:
{{
  "back_cover_blurb": "sinopsis de contraportada, 80-150 palabras, que \
enganche a un lector en una librería sin revelar el final",
  "keywords": ["5 a 7 palabras o frases cortas de búsqueda/descubribilidad"],
  "categories": ["2 a 3 categorías de género, estilo BISAC, en {language_name}"]
}}
"""


def generate_kdp_metadata(
    metadata: BookMetadata, chapters: list[Chapter], excerpt_chars: int = 600
) -> KDPMetadata:
    lang_meta = SUPPORTED_LANGUAGES[metadata.language]
    excerpt = _first_chapter_excerpt(chapters, excerpt_chars)

    prompt = _PROMPT_TEMPLATE.format(
        language_name=lang_meta["name"],
        title=metadata.title,
        subtitle=metadata.subtitle or "(sin subtítulo)",
        author=metadata.author,
        genre=metadata.genre or "(no especificado, infiérelo del texto)",
        excerpt=excerpt,
    )

    logger.info("Generando metadatos comerciales con IA (idioma=%s)", metadata.language)
    data = generate_json(prompt, required_fields=_REQUIRED_FIELDS)

    return KDPMetadata(
        back_cover_blurb=str(data["back_cover_blurb"]).strip(),
        keywords=[str(k).strip() for k in data.get("keywords", []) if str(k).strip()],
        categories=[str(c).strip() for c in data.get("categories", []) if str(c).strip()],
    )


def _first_chapter_excerpt(chapters: list[Chapter], max_chars: int) -> str:
    if not chapters:
        return "(manuscrito sin capítulos detectados)"
    import re

    plain = re.sub(r"<[^>]+>", " ", chapters[0].html_content)
    plain = re.sub(r"\s+", " ", plain).strip()
    return plain[:max_chars]
