"""Tests de core/cleaner.py — la tipografía correcta por idioma es el
valor editorial diferencial del proyecto, así que sus reglas merecen
tests explícitos, no solo inspección visual."""

from __future__ import annotations

from core.cleaner import NNBSP, normalize_manuscript_text


def test_spanish_uses_guillemets():
    result = normalize_manuscript_text('Dijo "hola" y se fue.', "es")
    assert "«hola»" in result


def test_english_uses_curly_quotes():
    result = normalize_manuscript_text('She said "hello" and left.', "en")
    assert "\u201chello\u201d" in result


def test_french_applies_thin_nbsp_before_punctuation():
    result = normalize_manuscript_text("Il a dit : bonjour !", "fr")
    assert f"{NNBSP}:" in result
    assert f"{NNBSP}!" in result


def test_hyphenated_linebreak_is_joined():
    result = normalize_manuscript_text("infor-\nmación completa", "es")
    assert "información completa" in result


def test_multiple_blank_lines_collapse_to_one_paragraph_break():
    result = normalize_manuscript_text("Párrafo uno.\n\n\n\nPárrafo dos.", "es")
    assert "\n\n\n" not in result


def test_unsupported_language_raises():
    import pytest

    from core.errors import PipelineError

    with pytest.raises(PipelineError):
        normalize_manuscript_text("texto", "de")
