"""
core/book_builder.py — Orquesta el pipeline completo, de manuscrito a
PDF maquetado:

    extractor -> cleaner -> structure_detector -> front_matter (IA)
    -> layout engine

Se puede usar como librería (función `build_book`) desde app.py, o
ejecutar directamente por línea de comandos.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from ai import front_matter as front_matter_generator
from ai import kdp_metadata as kdp_metadata_generator
from ai import quality_check
from config import DEFAULT_TEMPLATE, SUPPORTED_LANGUAGES
from core import cleaner, extractor, structure_detector
from core.errors import AIProviderError, PipelineError
from layout import engine as layout_engine
from models.book import BookMetadata, BookProject
from utils.logging import get_logger, timer

logger = get_logger(__name__)

ProgressCallback = Optional[Callable[[str], None]]


def build_book(
    manuscript_path: str | Path,
    metadata: BookMetadata,
    dedication_hint: str | None = None,
    template_name: str = DEFAULT_TEMPLATE,
    output_path: str | Path | None = None,
    on_progress: ProgressCallback = None,
    generate_kdp_metadata: bool = True,
    run_quality_check: bool = True,
) -> BookProject:
    """Ejecuta el pipeline completo y devuelve el BookProject resultante,
    con `output_pdf_path` y `estimated_page_count` ya rellenos.

    `on_progress`, si se proporciona, se llama con una etiqueta legible
    al empezar cada fase real del pipeline — pensado para conectar una
    barra de estado en la UI al progreso real, no a una simulación fija.

    `generate_kdp_metadata` y `run_quality_check` son pasos de IA
    OPCIONALES y no bloqueantes (ver ai/kdp_metadata.py y
    ai/quality_check.py): si fallan, el libro se compone igual — el
    PDF nunca depende de que estas dos extensiones funcionen.
    """
    if metadata.language not in SUPPORTED_LANGUAGES:
        raise PipelineError(f"Idioma no soportado: {metadata.language}")

    project = BookProject(metadata=metadata)

    with timer(logger, "Extracción de texto", on_step=on_progress):
        manuscript = extractor.extract_manuscript(manuscript_path)

    with timer(logger, "Limpieza y normalización tipográfica", on_step=on_progress):
        manuscript.raw_text = cleaner.normalize_manuscript_text(
            manuscript.raw_text, metadata.language
        )
        manuscript.detected_language = metadata.language
        manuscript.char_count = len(manuscript.raw_text)
    project.manuscript = manuscript

    with timer(logger, "Detección de estructura de capítulos", on_step=on_progress):
        project.chapters = structure_detector.detect_chapters(
            manuscript.raw_text, metadata.language
        )

    with timer(logger, "Generación de front matter (IA)", on_step=on_progress):
        project.front_matter = front_matter_generator.generate_front_matter(
            metadata, dedication_hint=dedication_hint
        )

    # --- Extensiones de IA opcionales: nunca detienen el pipeline ---
    if generate_kdp_metadata:
        with timer(logger, "Metadatos comerciales KDP (IA, opcional)", on_step=on_progress):
            try:
                project.kdp_metadata = kdp_metadata_generator.generate_kdp_metadata(
                    metadata, project.chapters
                )
            except AIProviderError as exc:
                logger.warning("Metadatos KDP omitidos (fallo de IA no bloqueante): %s", exc)

    if run_quality_check:
        with timer(logger, "Control de calidad editorial (IA, opcional)", on_step=on_progress):
            try:
                project.quality_warnings = quality_check.check_manuscript_consistency(
                    manuscript.raw_text, metadata.language
                )
            except AIProviderError as exc:
                logger.warning("Control de calidad omitido (fallo de IA no bloqueante): %s", exc)

    # La composición (2 pasadas del motor de render) ya loguea sus
    # propios tiempos internamente y reporta progreso vía on_progress,
    # ver layout/engine.py.
    layout_engine.compose_pdf(
        project, template_name=template_name, output_path=output_path, on_step=on_progress
    )

    logger.info(
        "Libro '%s' compuesto: %d capítulos, %d páginas -> %s",
        metadata.title, len(project.chapters),
        project.estimated_page_count, project.output_pdf_path,
    )
    return project


def _run_cli() -> None:
    print("=== DashBook IA Maquetación — línea de comandos ===\n")

    manuscript_path = input("Ruta del manuscrito (PDF/DOCX/TXT/MD): ").strip().strip('"')
    title = input("Título del libro: ").strip()
    author = input("Autor/a: ").strip()

    print("\nIdiomas disponibles: " + ", ".join(
        f"{code} ({meta['name']})" for code, meta in SUPPORTED_LANGUAGES.items()
    ))
    language = input("Código de idioma [es]: ").strip() or "es"

    year_raw = input("Año de publicación [actual]: ").strip()
    from datetime import date
    year = int(year_raw) if year_raw else date.today().year

    trim_size = input("Trim size [6x9]: ").strip() or "6x9"

    metadata = BookMetadata(
        title=title,
        author=author,
        language=language,
        year=year,
        trim_size=trim_size,
    )

    try:
        project = build_book(manuscript_path, metadata, on_progress=lambda step: print(f"→ {step}"))
    except PipelineError as exc:
        print(f"\n✗ Error: {exc}")
        return

    print(f"\n✔ Listo: {project.output_pdf_path}")
    print(f"  Páginas: {project.estimated_page_count}")
    print(f"  Capítulos: {len(project.chapters)}")


if __name__ == "__main__":
    _run_cli()
