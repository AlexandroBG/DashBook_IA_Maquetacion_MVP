"""Tests de layout/kdp_rules.py — el cálculo del gutter dinámico es uno
de los pocos sitios del proyecto donde un error numérico se traduce
directamente en un libro mal encuadernado, así que merece cobertura
explícita de sus límites de tramo."""

from __future__ import annotations

import pytest

from layout.kdp_rules import (
    gutter_for_page_count,
    resolve_trim_size,
)


@pytest.mark.parametrize(
    "page_count, expected_gutter",
    [
        (10, 0.375),  # por debajo del mínimo KDP -> tramo más bajo
        (24, 0.375),  # límite inferior del primer tramo
        (150, 0.375),  # límite superior del primer tramo
        (151, 0.5),  # primer valor del segundo tramo
        (300, 0.5),
        (301, 0.625),
        (500, 0.625),
        (501, 0.75),
        (700, 0.75),
        (701, 0.875),
        (828, 0.875),
        (2000, 0.875),  # por encima del máximo típico -> tramo más alto
    ],
)
def test_gutter_for_page_count_boundaries(page_count, expected_gutter):
    assert gutter_for_page_count(page_count) == expected_gutter


def test_resolve_trim_size_known_key():
    assert resolve_trim_size("6x9") == (6.0, 9.0)


def test_resolve_trim_size_unknown_key_raises():
    with pytest.raises(ValueError):
        resolve_trim_size("no-existe")
