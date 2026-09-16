"""
app.py — Interfaz Streamlit de DashBook IA Maquetación.

Capa fina sobre core.book_builder.build_book(): toda la lógica real
vive en el backend (extractor, cleaner, structure_detector, ai/,
layout/). Esta interfaz solo recoge inputs, llama al pipeline y
muestra el resultado.
"""

from __future__ import annotations

import tempfile
from datetime import date
from pathlib import Path

import streamlit as st

from config import SAMPLE_DIR, SUPPORTED_LANGUAGES, validate_config
from core.book_builder import build_book
from core.errors import AIProviderError, PipelineError
from layout.kdp_rules import TRIM_SIZES
from models.book import BookMetadata
from utils.logging import get_logger

logger = get_logger(__name__)

st.set_page_config(page_title="DashBook IA Maquetación", page_icon="📖", layout="centered")

st.title("📖 DashBook IA Maquetación")
st.caption(
    "Convierte un manuscrito en un libro maquetado con paginación real, "
    "listo para imprenta o Amazon KDP."
)

# ---------------------------------------------------------------------------
# Fail-fast: si falta configuración de IA, se avisa ANTES de aceptar
# cualquier manuscrito, no a mitad del pipeline.
# ---------------------------------------------------------------------------
_config_problems = validate_config()
if _config_problems:
    st.error(
        "⚠️ Configuración incompleta. Revisa tu archivo `.env` antes de continuar:\n\n"
        + "\n".join(f"- {p}" for p in _config_problems)
    )
    st.stop()

# ---------------------------------------------------------------------------
# Demo rápida: manuscrito de ejemplo precargado, para poder ver el
# pipeline completo en marcha sin depender de que el usuario tenga un
# manuscrito a mano.
# ---------------------------------------------------------------------------
use_sample = st.checkbox(
    "🚀 Usar manuscrito de ejemplo (demo rápida, 3 capítulos en español)"
)

with st.form("book_form"):
    st.subheader("1. Manuscrito")
    uploaded_file = None
    if not use_sample:
        uploaded_file = st.file_uploader(
            "Sube el manuscrito (PDF, DOCX, TXT o Markdown)",
            type=["pdf", "docx", "txt", "md", "markdown"],
        )
    else:
        st.info("Se usará el manuscrito de ejemplo incluido en el proyecto.")

    st.subheader("2. Metadatos del libro")
    col1, col2 = st.columns(2)
    with col1:
        title = st.text_input("Título *", value="El faro apagado" if use_sample else "")
        author = st.text_input("Autor/a *", value="Autor de ejemplo" if use_sample else "")
        year = st.number_input(
            "Año de publicación", min_value=1900, max_value=2100, value=date.today().year
        )
    with col2:
        subtitle = st.text_input("Subtítulo (opcional)")
        publisher = st.text_input("Editorial", value="DashBook")
        isbn = st.text_input("ISBN (opcional)")
        genre = st.text_input(
            "Género / tipo de libro (opcional)",
            placeholder="Novela, poesía, ensayo, infantil...",
        )

    language_label_to_code = {meta["name"]: code for code, meta in SUPPORTED_LANGUAGES.items()}
    language_label = st.selectbox("Idioma del manuscrito *", list(language_label_to_code.keys()))
    language = language_label_to_code[language_label]

    trim_size = st.selectbox(
        "Trim size (tamaño de página)",
        list(TRIM_SIZES.keys()),
        index=list(TRIM_SIZES.keys()).index("6x9"),
    )
    include_toc = st.checkbox("Incluir índice (tabla de contenidos)", value=True)
    dedication_hint = st.text_area(
        "Dedicatoria (opcional — la IA la redacta a partir de esta idea)"
    )

    submitted = st.form_submit_button("Maquetar libro", type="primary", use_container_width=True)

if submitted:
    errors = []
    if not use_sample and not uploaded_file:
        errors.append("Falta subir el manuscrito (o marca la casilla de demo rápida).")
    if not title.strip():
        errors.append("Falta el título.")
    if not author.strip():
        errors.append("Falta el autor/a.")

    if errors:
        for err in errors:
            st.error(err)
    else:
        with tempfile.TemporaryDirectory() as tmp_dir:
            if use_sample:
                tmp_path = SAMPLE_DIR / "manuscrito_ejemplo_es.txt"
            else:
                tmp_path = Path(tmp_dir) / uploaded_file.name
                tmp_path.write_bytes(uploaded_file.getvalue())

            metadata = BookMetadata(
                title=title.strip(),
                subtitle=subtitle.strip() or None,
                author=author.strip(),
                language=language,
                publisher=publisher.strip() or "DashBook",
                isbn=isbn.strip() or None,
                year=int(year),
                trim_size=trim_size,
                include_toc=include_toc,
                genre=genre.strip() or None,
            )

            status = st.status("Maquetando el libro...", expanded=True)

            def _report_progress(step_label: str) -> None:
                status.write(f"▶ {step_label}...")

            try:
                project = build_book(
                    manuscript_path=tmp_path,
                    metadata=metadata,
                    dedication_hint=dedication_hint.strip() or None,
                    on_progress=_report_progress,
                )

                status.update(label="✔ Libro maquetado con éxito", state="complete", expanded=False)

                st.success(
                    f"**{project.metadata.title}** — {len(project.chapters)} capítulos, "
                    f"{project.estimated_page_count} páginas, "
                    f"gutter {project.layout_spec.margin_gutter_in:.3f}\""
                )

                pdf_bytes = Path(project.output_pdf_path).read_bytes()
                st.download_button(
                    "⬇️ Descargar PDF maquetado",
                    data=pdf_bytes,
                    file_name=Path(project.output_pdf_path).name,
                    mime="application/pdf",
                    use_container_width=True,
                )

                with st.expander("Detalle de capítulos detectados"):
                    for ch in project.chapters:
                        st.write(f"{ch.order}. {ch.title}  ·  _detectado por {ch.detected_by}_")

                if project.kdp_metadata:
                    with st.expander("📋 Ficha comercial generada por IA (KDP)", expanded=True):
                        st.markdown(f"**Sinopsis de contraportada**\n\n{project.kdp_metadata.back_cover_blurb}")
                        if project.kdp_metadata.keywords:
                            st.markdown("**Palabras clave:** " + ", ".join(project.kdp_metadata.keywords))
                        if project.kdp_metadata.categories:
                            st.markdown("**Categorías:** " + ", ".join(project.kdp_metadata.categories))

                if project.quality_warnings:
                    with st.expander(
                        f"⚠️ Observaciones de calidad a revisar ({len(project.quality_warnings)})"
                    ):
                        st.caption(
                            "Sugerencias de la IA para que un editor humano las confirme — "
                            "no se ha modificado ni una palabra del manuscrito."
                        )
                        for warning in project.quality_warnings:
                            st.write(f"• {warning}")

            except AIProviderError as exc:
                status.update(label="✗ Error con el proveedor de IA", state="error")
                st.error(f"Problema con el proveedor de IA configurado: {exc}")
            except PipelineError as exc:
                status.update(label="✗ Error en el pipeline", state="error")
                st.error(str(exc))
            except Exception as exc:  # noqa: BLE001 — mostramos cualquier fallo inesperado
                status.update(label="✗ Error inesperado", state="error")
                logger.exception("Fallo inesperado en el pipeline")
                st.error(f"Error inesperado: {exc}")

st.divider()
st.caption(
    "DashBook IA Maquetación · Motor de composición: WeasyPrint (CSS Paged Media) · "
    "Front matter y detección de estructura asistidos por IA (proveedor configurable en .env)."
)
