"""
layout/render_backend.py — Interfaz de motor de render, y la única
implementación actual (WeasyPrint).

Por qué existe esta capa (ver evaluación técnica del proyecto): dentro
de la familia CSS Paged Media, WeasyPrint es una opción sólida y
gratuita, pero no la de mayor precisión disponible (motores comerciales
como Prince XML son el estándar de facto en varias editoriales reales
para este mismo flujo HTML→PDF). Como book_builder y las plantillas
Jinja2 no dependen de WeasyPrint directamente, sino de esta interfaz,
en el futuro se puede añadir una `PrinceRenderBackend` sin tocar nada
más del proyecto — solo comparar resultados y, si compensa, cambiar
`DEFAULT_BACKEND` o pasarlo explícitamente en compose_pdf().

No se ha añadido esa segunda implementación en este MVP para no
introducir una dependencia comercial sin validar antes, con el
manuscrito real de la editorial, si el salto de calidad lo justifica.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class RenderedDocument(ABC):
    """Documento ya compuesto por un backend de render."""

    @property
    @abstractmethod
    def page_count(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def write_pdf(self, target: Path) -> None:
        raise NotImplementedError


class RenderBackend(ABC):
    """Motor de composición HTML+CSS -> PDF paginado.

    Cualquier implementación debe soportar CSS Paged Media (@page,
    márgenes espejo :left/:right, target-counter para el índice,
    orphans/widows) — son las funcionalidades que layout/engine.py y
    las plantillas de layout/templates/ dan por sentadas.
    """

    @abstractmethod
    def render(self, html: str, base_url: str) -> RenderedDocument:
        raise NotImplementedError


class WeasyPrintDocument(RenderedDocument):
    def __init__(self, document) -> None:
        self._document = document

    @property
    def page_count(self) -> int:
        return len(self._document.pages)

    def write_pdf(self, target: Path) -> None:
        self._document.write_pdf(target=str(target))


class WeasyPrintBackend(RenderBackend):
    """Backend de render por defecto del proyecto."""

    def render(self, html: str, base_url: str) -> RenderedDocument:
        from weasyprint import HTML

        document = HTML(string=html, base_url=base_url).render()
        return WeasyPrintDocument(document)


def get_default_backend() -> RenderBackend:
    return WeasyPrintBackend()
