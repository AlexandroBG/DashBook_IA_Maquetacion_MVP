"""Tests de ai/kdp_metadata.py — comprueba el contrato de datos sin red,
sustituyendo ai.client.generate_json por un doble de prueba."""

from __future__ import annotations

import ai.kdp_metadata as kdp_metadata_module
from models.book import BookMetadata, Chapter


def _fake_generate_json(prompt, required_fields=None):
    return {
        "back_cover_blurb": "Una historia breve sobre un faro y un secreto.",
        "keywords": ["faro", "misterio", "costa"],
        "categories": ["Ficción", "Misterio"],
    }


def test_generate_kdp_metadata_returns_expected_fields(monkeypatch):
    monkeypatch.setattr(kdp_metadata_module, "generate_json", _fake_generate_json)

    metadata = BookMetadata(
        title="El faro apagado", author="Autora", language="es", year=2026, genre="Novela"
    )
    chapters = [
        Chapter(order=1, title="Cap 1", html_content="<p>Texto de ejemplo.</p>", detected_by="heuristic")
    ]

    result = kdp_metadata_module.generate_kdp_metadata(metadata, chapters)

    assert result.back_cover_blurb
    assert result.keywords == ["faro", "misterio", "costa"]
    assert result.categories == ["Ficción", "Misterio"]


def test_generate_kdp_metadata_handles_empty_chapters(monkeypatch):
    monkeypatch.setattr(kdp_metadata_module, "generate_json", _fake_generate_json)

    metadata = BookMetadata(title="T", author="A", language="fr", year=2026)
    result = kdp_metadata_module.generate_kdp_metadata(metadata, [])

    assert result.back_cover_blurb
