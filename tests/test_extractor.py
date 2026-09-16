"""Tests de core/extractor.py — cubren el camino más simple (TXT) y los
errores de negocio que el usuario debe ver con mensaje claro."""

from __future__ import annotations

from pathlib import Path

import pytest

from core.errors import PipelineError
from core.extractor import extract_manuscript
from models.book import InputFormat


def test_extract_plain_txt(tmp_path: Path):
    sample = tmp_path / "manuscrito.txt"
    sample.write_text("Capítulo 1\r\n\r\nHola mundo.\r\n", encoding="utf-8")

    manuscript = extract_manuscript(sample)

    assert manuscript.source_format == InputFormat.TXT
    assert "\r" not in manuscript.raw_text
    assert "Hola mundo." in manuscript.raw_text


def test_extract_missing_file_raises():
    with pytest.raises(PipelineError):
        extract_manuscript("/ruta/que/no/existe.txt")


def test_extract_unsupported_extension_raises(tmp_path: Path):
    sample = tmp_path / "manuscrito.epub"
    sample.write_text("contenido", encoding="utf-8")
    with pytest.raises(PipelineError):
        extract_manuscript(sample)


def test_extract_empty_file_raises(tmp_path: Path):
    sample = tmp_path / "vacio.txt"
    sample.write_text("   \n\n  ", encoding="utf-8")
    with pytest.raises(PipelineError):
        extract_manuscript(sample)
