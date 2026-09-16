"""
config.py — Configuración global de DashBook IA Maquetación.

Centraliza rutas, idiomas soportados, configuración del proveedor de IA
y constantes tipográficas que usa el resto de módulos. Ningún otro
módulo debería leer os.environ directamente: todo pasa por aquí.

Esquema de variables de entorno (.env):

    AI_PROVIDER=gemini        # proveedor a usar (ver ai/providers/)
    AI_API_KEY=...            # clave del proveedor seleccionado
    AI_MODEL=gemini-2.5-flash # modelo del proveedor seleccionado

Por compatibilidad con versiones anteriores del proyecto, si no se
definen AI_API_KEY / AI_MODEL se aceptan también GEMINI_API_KEY /
GEMINI_MODEL. Cambiar de modelo o de proveedor es, en el caso normal,
solo cuestión de editar el .env — ver README para más detalle.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Rutas del proyecto
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "layout" / "templates"
DATA_DIR = BASE_DIR / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
SAMPLE_DIR = DATA_DIR / "sample"
LOGS_DIR = BASE_DIR / "logs"

for _dir in (INPUT_DIR, OUTPUT_DIR, LOGS_DIR):
    _dir.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Variables de entorno
# ---------------------------------------------------------------------------

load_dotenv(BASE_DIR / ".env")


def _env(*names: str, default: str = "") -> str:
    """Devuelve el valor de la primera variable de entorno definida entre
    `names`. Permite mantener compatibilidad con nombres antiguos
    (GEMINI_API_KEY) mientras se promueve el nuevo esquema genérico
    (AI_API_KEY), sin que ningún otro módulo tenga que saberlo.
    """
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return default


# Proveedor de IA activo. Debe existir una clase registrada para este
# nombre en ai/client.py (ver ese módulo para añadir un proveedor nuevo).
AI_PROVIDER = _env("AI_PROVIDER", default="gemini")

# Clave y modelo del proveedor activo. Se aceptan también GEMINI_API_KEY /
# GEMINI_MODEL por compatibilidad con instalaciones existentes.
AI_API_KEY = _env("AI_API_KEY", "GEMINI_API_KEY")
AI_MODEL = _env("AI_MODEL", "GEMINI_MODEL", default="gemini-2.5-flash")

# Reintentos ante errores transitorios del proveedor de IA (rate limit, 5xx).
AI_MAX_RETRIES = int(_env("AI_MAX_RETRIES", "GEMINI_MAX_RETRIES", default="4"))

# ---------------------------------------------------------------------------
# Idiomas soportados
# ---------------------------------------------------------------------------
# Código ISO 639-1 -> metadatos tipográficos y editoriales del idioma.
# `hyphen_lang` es el código que usa Pyphen/WeasyPrint para guionado.
# `quote_style` determina qué comillas usa cleaner.py al normalizar texto.

SUPPORTED_LANGUAGES: dict[str, dict] = {
    "es": {
        "name": "Español (castellano)",
        "hyphen_lang": "es",
        "quote_style": "guillemets",  # « texto »
        "chapter_markers": ["capítulo", "capitulo", "parte", "libro"],
        "toc_title": "Índice",
        "part_word": "Parte",
        "chapter_word": "Capítulo",
    },
    "ca": {
        "name": "Català",
        "hyphen_lang": "ca",
        "quote_style": "guillemets",
        "chapter_markers": ["capítol", "capitol", "part", "llibre"],
        "toc_title": "Índex",
        "part_word": "Part",
        "chapter_word": "Capítol",
    },
    "fr": {
        "name": "Français",
        "hyphen_lang": "fr",
        "quote_style": "guillemets_nbsp",  # « texto » con espacio fino insecable
        "chapter_markers": ["chapitre", "partie", "livre"],
        "toc_title": "Table des matières",
        "part_word": "Partie",
        "chapter_word": "Chapitre",
    },
    "it": {
        "name": "Italiano",
        "hyphen_lang": "it",
        "quote_style": "guillemets",
        "chapter_markers": ["capitolo", "parte", "libro"],
        "toc_title": "Indice",
        "part_word": "Parte",
        "chapter_word": "Capitolo",
    },
    "en": {
        "name": "English",
        "hyphen_lang": "en-us",
        "quote_style": "curly",  # " texto "
        "chapter_markers": ["chapter", "part", "book"],
        "toc_title": "Contents",
        "part_word": "Part",
        "chapter_word": "Chapter",
    },
}

DEFAULT_LANGUAGE = "es"

# Patrones universales que aplican en cualquier idioma (numerales romanos,
# "1", "01", etc.) además de los `chapter_markers` propios del idioma.
UNIVERSAL_CHAPTER_MARKERS = [
    r"^\s*\d{1,3}\s*$",  # "1", "23"
    r"^\s*[IVXLCDM]{1,8}\s*$",  # números romanos
]

# ---------------------------------------------------------------------------
# Formatos de entrada soportados
# ---------------------------------------------------------------------------

SUPPORTED_INPUT_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".markdown"}

# ---------------------------------------------------------------------------
# Parámetros de maquetación por defecto
# ---------------------------------------------------------------------------

DEFAULT_TRIM_SIZE = "6x9"  # ver layout/kdp_rules.py para el catálogo completo
DEFAULT_TEMPLATE = "novel"

# Control de viudas/huérfanas (líneas mínimas que deben quedar juntas
# al inicio/fin de página). 2 es el estándar editorial.
DEFAULT_ORPHANS = 2
DEFAULT_WIDOWS = 2

MAX_CHAPTER_DETECTION_CHARS_FOR_LLM = 12000  # tope de contexto enviado a la IA

# ---------------------------------------------------------------------------
# Validación de configuración
# ---------------------------------------------------------------------------


def validate_config() -> list[str]:
    """Valida la configuración mínima para ejecutar el pipeline.

    Devuelve una lista de problemas (vacía si todo está bien). Pensado
    para llamarse al arrancar la interfaz, ANTES de aceptar un manuscrito,
    para no descubrir un .env mal configurado a mitad del proceso.
    """
    problems: list[str] = []
    if not AI_API_KEY:
        problems.append(
            "Falta AI_API_KEY en el archivo .env (o GEMINI_API_KEY, por compatibilidad)."
        )
    if AI_PROVIDER.lower() not in ("gemini",):
        problems.append(
            f"AI_PROVIDER='{AI_PROVIDER}' no está soportado todavía. "
            f"Proveedores disponibles: gemini."
        )
    return problems
