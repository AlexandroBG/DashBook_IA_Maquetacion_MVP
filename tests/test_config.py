"""Tests de configuración: validate_config debe detectar los problemas
reales que impedirían ejecutar el pipeline, sin falsos positivos."""

from __future__ import annotations

import config


def test_validate_config_detects_missing_api_key(monkeypatch):
    monkeypatch.setattr(config, "AI_API_KEY", "")
    monkeypatch.setattr(config, "AI_PROVIDER", "gemini")
    problems = config.validate_config()
    assert any("AI_API_KEY" in p for p in problems)


def test_validate_config_detects_unsupported_provider(monkeypatch):
    monkeypatch.setattr(config, "AI_API_KEY", "clave-de-prueba")
    monkeypatch.setattr(config, "AI_PROVIDER", "proveedor-inexistente")
    problems = config.validate_config()
    assert any("proveedor-inexistente" in p for p in problems)


def test_validate_config_ok_with_valid_setup(monkeypatch):
    monkeypatch.setattr(config, "AI_API_KEY", "clave-de-prueba")
    monkeypatch.setattr(config, "AI_PROVIDER", "gemini")
    assert config.validate_config() == []
