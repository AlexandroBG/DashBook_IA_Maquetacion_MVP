"""
ai/quality_check.py — Señala posibles inconsistencias editoriales
(nombres escritos de dos formas distintas, fechas contradictorias,
etc.) para que un editor humano decida.

Regla estricta, igual que en el resto de ai/: esto NUNCA modifica el
texto del autor. Solo devuelve una lista de observaciones en texto
plano para mostrarlas en la UI antes de mandar a imprenta — la
decisión de corregir algo es siempre humana.

Paso OPCIONAL del pipeline: si falla, el libro se compone igual — ver
core/book_builder.py.
"""

from __future__ import annotations

from ai.client import generate_json
from config import MAX_CHAPTER_DETECTION_CHARS_FOR_LLM, SUPPORTED_LANGUAGES
from utils.logging import get_logger

logger = get_logger(__name__)

_PROMPT_TEMPLATE = """Eres un corrector editorial. Lee el siguiente \
manuscrito (o un extracto representativo) en {language_name} y señala \
SOLO inconsistencias objetivas y verificables: nombres de personajes o \
lugares escritos de más de una forma, fechas o edades que se \
contradicen entre sí, cambios de nombre sin explicación aparente.

NO señales cuestiones de estilo, gusto literario ni gramática. NO \
corrijas ni reescribas nada: solo describe cada inconsistencia en una \
frase breve, citando las dos formas que entran en conflicto. Si no \
encuentras ninguna inconsistencia clara, devuelve una lista vacía — no \
inventes problemas para rellenar.

Responde EXCLUSIVAMENTE con este JSON, sin texto adicional ni \
backticks de Markdown:
{{"warnings": ["observación breve 1", "observación breve 2", ...]}}

--- MANUSCRITO (posible extracto) ---
{text_sample}
"""


def check_manuscript_consistency(raw_text: str, language: str) -> list[str]:
    """Devuelve una lista de observaciones (puede estar vacía). Nunca
    lanza excepción por 'no encontrar nada' — solo por fallo real de
    comunicación con el proveedor de IA (ver AIProviderError, atrapado
    por quien llame a esta función si el chequeo es opcional).
    """
    lang_name = SUPPORTED_LANGUAGES[language]["name"]
    sample = raw_text[:MAX_CHAPTER_DETECTION_CHARS_FOR_LLM]
    prompt = _PROMPT_TEMPLATE.format(language_name=lang_name, text_sample=sample)

    logger.info("Ejecutando control de calidad editorial con IA (idioma=%s)", language)
    data = generate_json(prompt, required_fields={"warnings"})

    warnings = data.get("warnings", [])
    if not isinstance(warnings, list):
        return []
    return [str(w).strip() for w in warnings if str(w).strip()]
