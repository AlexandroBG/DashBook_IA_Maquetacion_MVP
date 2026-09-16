"""Tests de ai/ — comprueban que la abstracción de proveedor funciona
sin depender de red: se sustituye el cliente interno de Gemini por un
doble de prueba, igual que se sustituiría por cualquier otro proveedor
futuro sin tocar structure_detector.py ni ai/front_matter.py."""

from __future__ import annotations

import pytest

from ai.providers.gemini import GeminiProvider
from core.errors import AIProviderError


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeModels:
    def __init__(self, response_text: str) -> None:
        self._response_text = response_text

    def generate_content(self, model: str, contents: str) -> _FakeResponse:
        return _FakeResponse(self._response_text)


class _FakeClient:
    def __init__(self, response_text: str) -> None:
        self.models = _FakeModels(response_text)


def _provider_with_fake_response(response_text: str) -> GeminiProvider:
    provider = GeminiProvider(api_key="clave-de-prueba", model="modelo-de-prueba")
    provider._client = _FakeClient(response_text)  # evita conectar de verdad
    return provider


def test_generate_json_parses_clean_json():
    provider = _provider_with_fake_response('{"chapter_titles": ["Uno", "Dos"]}')
    result = provider.generate_json("prompt cualquiera")
    assert result == {"chapter_titles": ["Uno", "Dos"]}


def test_generate_json_strips_markdown_fences():
    provider = _provider_with_fake_response('```json\n{"half_title": "El faro"}\n```')
    result = provider.generate_json("prompt cualquiera")
    assert result == {"half_title": "El faro"}


def test_generate_json_invalid_json_raises_ai_provider_error():
    provider = _provider_with_fake_response("esto no es JSON")
    with pytest.raises(AIProviderError):
        provider.generate_json("prompt cualquiera")


def test_missing_api_key_raises_immediately():
    with pytest.raises(AIProviderError):
        GeminiProvider(api_key="", model="modelo-de-prueba")
