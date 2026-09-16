"""
layout/kdp_rules.py — Catálogo de tamaños de recorte (trim sizes) y
reglas de márgenes de Amazon KDP para impresión bajo demanda (libros en
blanco y negro, papel crema o blanco, encuadernación tapa blanda).

Fuente: especificaciones públicas de KDP Print. Si la editorial imprime
con un proveedor distinto de KDP, estos valores son un punto de partida
razonable, pero SIEMPRE hay que validar contra los requisitos exactos
del proveedor final antes de enviar el archivo (ver README).
"""

from __future__ import annotations

from models.book import LayoutSpec

# (ancho, alto) en pulgadas — tamaños más usados para novela / no ficción.
TRIM_SIZES: dict[str, tuple[float, float]] = {
    "5x8": (5.0, 8.0),
    "5.25x8": (5.25, 8.0),
    "5.5x8.5": (5.5, 8.5),
    "6x9": (6.0, 9.0),
    "5.06x7.81": (5.06, 7.81),
    "6.14x9.21": (6.14, 9.21),
    "7x10": (7.0, 10.0),
    "8.5x11": (8.5, 11.0),
}

# Márgenes mínimos exteriores/superior/inferior recomendados por KDP para
# libros interiores en B/N. No dependen del nº de páginas.
MARGIN_TOP_IN = 0.75
MARGIN_BOTTOM_IN = 0.75
MARGIN_OUTSIDE_IN = 0.5

# Gutter (margen de lomo/encuadernación) dinámico según el número total
# de páginas del libro — a más páginas, más papel "se come" el pliegue
# de la encuadernación, así que el margen interior debe crecer.
# Tabla oficial de KDP Print (páginas -> gutter en pulgadas).
_GUTTER_TABLE: list[tuple[int, int, float]] = [
    (24, 150, 0.375),
    (151, 300, 0.5),
    (301, 500, 0.625),
    (501, 700, 0.75),
    (701, 828, 0.875),
]

MAX_KDP_PAGES = 828
MIN_KDP_PAGES = 24


def gutter_for_page_count(page_count: int) -> float:
    """Devuelve el margen de lomo correspondiente al número de páginas.

    Aplica el mismo margen del tramo más cercano si el libro cae fuera
    del rango típico de KDP (muy corto o, en teoría, más largo del
    máximo soportado), en vez de fallar.
    """
    if page_count < MIN_KDP_PAGES:
        return _GUTTER_TABLE[0][2]
    for low, high, gutter in _GUTTER_TABLE:
        if low <= page_count <= high:
            return gutter
    return _GUTTER_TABLE[-1][2]


def resolve_trim_size(trim_size_key: str) -> tuple[float, float]:
    if trim_size_key not in TRIM_SIZES:
        raise ValueError(
            f"Trim size '{trim_size_key}' no reconocido. Opciones: {', '.join(TRIM_SIZES)}"
        )
    return TRIM_SIZES[trim_size_key]


def build_layout_spec(
    trim_size_key: str,
    estimated_page_count: int,
    orphans: int = 2,
    widows: int = 2,
) -> LayoutSpec:
    """Construye el LayoutSpec final combinando trim size + gutter dinámico.

    `estimated_page_count` es una PRIMERA estimación (ver core/book_builder.py,
    que hace una pasada de renderizado previa para contar páginas reales
    antes de fijar el gutter definitivo — el número de páginas cambia
    ligeramente según el margen, así que book_builder itera si hace falta).
    """
    width, height = resolve_trim_size(trim_size_key)
    gutter = gutter_for_page_count(estimated_page_count)
    return LayoutSpec(
        trim_width_in=width,
        trim_height_in=height,
        margin_top_in=MARGIN_TOP_IN,
        margin_bottom_in=MARGIN_BOTTOM_IN,
        margin_outside_in=MARGIN_OUTSIDE_IN,
        margin_gutter_in=gutter,
        orphans=orphans,
        widows=widows,
    )
