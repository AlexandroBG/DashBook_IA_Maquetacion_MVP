"""Tests de ai/quality_check.py — nunca debe modificar el texto, solo
devolver observaciones; se sustituye ai.client.generate_json."""

from __future__ import annotations

import ai.quality_check as quality_check_module


def test_check_manuscript_consistency_returns_warnings(monkeypatch):
    def _fake_generate_json(prompt, required_fields=None):
        return {"warnings": ["El personaje aparece como 'Elena' y 'Helena' en distintos puntos."]}

    monkeypatch.setattr(quality_check_module, "generate_json", _fake_generate_json)

    warnings = quality_check_module.check_manuscript_consistency("texto de ejemplo", "es")

    assert len(warnings) == 1
    assert "Elena" in warnings[0]


def test_check_manuscript_consistency_empty_when_no_issues(monkeypatch):
    def _fake_generate_json(prompt, required_fields=None):
        return {"warnings": []}

    monkeypatch.setattr(quality_check_module, "generate_json", _fake_generate_json)

    warnings = quality_check_module.check_manuscript_consistency("texto limpio", "fr")

    assert warnings == []


def test_check_manuscript_consistency_ignores_malformed_response(monkeypatch):
    def _fake_generate_json(prompt, required_fields=None):
        return {"warnings": "esto no es una lista"}

    monkeypatch.setattr(quality_check_module, "generate_json", _fake_generate_json)

    warnings = quality_check_module.check_manuscript_consistency("texto", "it")

    assert warnings == []
