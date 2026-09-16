"""
layout/engine.py — Motor de composición real del libro.

Toda la "maquetación" (numeración de página, saltos de página, índice
con números verdaderos, márgenes espejo con gutter dinámico, control de
viudas/huérfanas) la resuelve el backend de render (ver render_backend.py,
WeasyPrint por defecto) interpretando CSS Paged Media sobre el HTML ya
construido. Python nunca calcula "a mano" dónde cae una página: eso es
exactamente lo que NO debe hacer una IA ni un script ingenuo (ver
README, sección "Arquitectura").

Proceso en dos pasadas, porque el gutter correcto depende del número
final de páginas, y el número final de páginas depende (ligeramente)
del margen usado:

  1ª pasada: se renderiza con el gutter de una estimación de páginas
             (basada en recuento de palabras) para obtener un nº de
             páginas real.
  2ª pasada: se recalcula el gutter con el nº de páginas real de la
             1ª pasada y se renderiza el PDF definitivo.

En la inmensa mayoría de los casos ambas pasadas caen en el mismo tramo
de la tabla de gutter de layout/kdp_rules.py, así que el resultado no
cambia entre pasadas; pero cuando el libro está justo en el límite de
un tramo, la segunda pasada evita un desajuste de márgenes en la
versión final.
"""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import DEFAULT_ORPHANS, DEFAULT_WIDOWS, SUPPORTED_LANGUAGES, TEMPLATES_DIR
from core.errors import PipelineError
from layout.kdp_rules import build_layout_spec
from layout.render_backend import RenderBackend, get_default_backend
from models.book import BookProject, LayoutSpec
from utils.logging import get_logger, timer

logger = get_logger(__name__)

# Palabras por página, cifra editorial estándar para novela en cuerpo
# 11pt / trim 6x9 — solo se usa para la ESTIMACIÓN inicial de la 1ª
# pasada; el número real siempre se mide renderizando.
_WORDS_PER_PAGE_ESTIMATE = 290

_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(disabled_extensions=("css",)),
)


def compose_pdf(
    project: BookProject,
    template_name: str = "novel",
    output_path: str | Path | None = None,
    backend: RenderBackend | None = None,
    on_step=None,
) -> tuple[Path, int]:
    """Compone el PDF final del proyecto. Devuelve (ruta_pdf, nº_páginas).

    `backend` permite inyectar un motor de render distinto al por
    defecto (WeasyPrint) sin tocar el resto de esta función — ver
    layout/render_backend.py.
    """
    if not project.chapters:
        raise PipelineError("El proyecto no tiene capítulos para maquetar")
    if not project.front_matter:
        raise PipelineError("El proyecto no tiene front matter generado")

    backend = backend or get_default_backend()
    metadata = project.metadata

    with timer(logger, "Composición del PDF (1ª pasada — estimación)", on_step=on_step):
        estimated_pages = _estimate_page_count(project)
        layout_spec = build_layout_spec(
            metadata.trim_size, estimated_pages, DEFAULT_ORPHANS, DEFAULT_WIDOWS
        )
        html_doc = _render_html(project, layout_spec, template_name)
        first_pass_pages = backend.render(html_doc, str(TEMPLATES_DIR)).page_count

    with timer(logger, "Composición del PDF (2ª pasada — definitiva)", on_step=on_step):
        final_layout_spec = build_layout_spec(
            metadata.trim_size, first_pass_pages, DEFAULT_ORPHANS, DEFAULT_WIDOWS
        )
        html_doc_final = _render_html(project, final_layout_spec, template_name)
        rendered = backend.render(html_doc_final, str(TEMPLATES_DIR))
        page_count = rendered.page_count

        out_path = _resolve_output_path(project, output_path)
        rendered.write_pdf(out_path)

    logger.info(
        "PDF generado: %s (%d páginas, gutter=%.3f\")",
        out_path, page_count, final_layout_spec.margin_gutter_in,
    )
    project.layout_spec = final_layout_spec
    project.output_pdf_path = str(out_path)
    project.estimated_page_count = page_count
    return out_path, page_count


def _estimate_page_count(project: BookProject) -> int:
    total_words = sum(len(_strip_html(ch.html_content).split()) for ch in project.chapters)
    front_matter_pages = 4  # portadilla, portada, copyright, [dedicatoria/TOC aparte]
    if project.front_matter.dedication:
        front_matter_pages += 1
    if project.metadata.include_toc:
        front_matter_pages += 1
    body_pages = max(1, round(total_words / _WORDS_PER_PAGE_ESTIMATE))
    # Cada capítulo fuerza inicio en recto: añade en promedio media
    # página "perdida" por capítulo para no subestimar el gutter.
    body_pages += len(project.chapters) // 2
    return front_matter_pages + body_pages


def _strip_html(html_fragment: str) -> str:
    import re

    return re.sub(r"<[^>]+>", " ", html_fragment)


def _resolve_output_path(project: BookProject, output_path: str | Path | None) -> Path:
    from config import OUTPUT_DIR
    from utils.logging import ensure_within

    if output_path is not None:
        path = Path(output_path)
    else:
        safe_title = (
            "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in project.metadata.title)
            .strip()
            .replace(" ", "_")
        )
        path = OUTPUT_DIR / f"{safe_title or 'libro'}.pdf"
    path.parent.mkdir(parents=True, exist_ok=True)
    return ensure_within(path, OUTPUT_DIR) if path.parent == OUTPUT_DIR else path


def _render_html(project: BookProject, layout_spec: LayoutSpec, template_name: str) -> str:
    template = _jinja_env.get_template(f"{template_name}.html")
    base_css_path = TEMPLATES_DIR / f"{template_name}.css"
    base_css = base_css_path.read_text(encoding="utf-8")

    lang_meta = SUPPORTED_LANGUAGES[project.metadata.language]

    return template.render(
        metadata=project.metadata,
        front_matter=project.front_matter,
        chapters=project.chapters,
        language=lang_meta["hyphen_lang"],
        toc_title=lang_meta["toc_title"],
        page_geometry_css=_build_page_geometry_css(layout_spec),
        base_css=base_css,
    )


def _build_page_geometry_css(spec: LayoutSpec) -> str:
    """Genera las reglas @page con el tamaño de recorte y los márgenes
    espejo (gutter dinámico) para las páginas recto/verso.

    Página impar (:right, recto) -> el lomo queda a la IZQUIERDA.
    Página par  (:left,  verso)  -> el lomo queda a la DERECHA.

    También expone `--content-height` (alto de recorte menos márgenes
    superior/inferior) como variable CSS: es lo que usa `.full-page` en
    novel.css para centrar verticalmente portadilla/portada/copyright,
    sin depender de `height: 100%` (poco fiable en paginación CSS).
    """
    content_height_in = spec.trim_height_in - spec.margin_top_in - spec.margin_bottom_in
    return f"""
@page {{
  size: {spec.trim_width_in}in {spec.trim_height_in}in;
  margin-top: {spec.margin_top_in}in;
  margin-bottom: {spec.margin_bottom_in}in;
}}
@page :right {{
  margin-left: {spec.margin_gutter_in}in;
  margin-right: {spec.margin_outside_in}in;
}}
@page :left {{
  margin-right: {spec.margin_gutter_in}in;
  margin-left: {spec.margin_outside_in}in;
}}
body {{
  orphans: {spec.orphans};
  widows: {spec.widows};
  --content-height: {content_height_in}in;
}}
""".strip()
