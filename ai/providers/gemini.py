"""
ai/providers/gemini.py — Adaptador de Gemini (google-genai SDK) para la
interfaz AIProvider.

Toda la dependencia del SDK de Google vive exclusivamente en este
archivo: cliente, reintentos y limpieza/parseo de la respuesta JSON.
Ningún otro módulo del proyecto importa `google.genai` directamente.
"""

from __future__ import annotations

import json
import re

from tenacity import retry, stop_after_attempt, wait_exponential

from core.errors import AIProviderError
from utils.logging import get_logger

from .base import AIProvider

logger = get_logger(__name__)

_CODE_FENCE_RE = re.compile(r"^```(?:json)?|```$", re.MULTILINE)


class GeminiProvider(AIProvider):
    """Adaptador para la Gemini Developer API vía el SDK `google-genai`."""

    def __init__(self, api_key: str, model: str, max_retries: int = 4):
        if not api_key:
            raise AIProviderError(
                "AI_API_KEY no configurada en .env (proveedor: gemini)."
            )
        self._api_key = api_key
        self._model = model
        self._max_retries = max_retries
        self._client = None  # inicialización perezosa: no conecta hasta el primer uso

    def _get_client(self):
        if self._client is None:
            from google import genai  # import perezoso: evita cargar el SDK si no se usa

            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def generate_json(self, prompt: str) -> dict:
        try:
            return self._call_with_retry(prompt)
        except AIProviderError:
            raise
        except Exception as exc:  # conexión/cuota tras agotar reintentos
            raise AIProviderError(
                f"Fallo de comunicación con el proveedor de IA (gemini, modelo "
                f"'{self._model}') tras {self._max_retries} intentos: {exc}"
            ) from exc

    def _call_with_retry(self, prompt: str) -> dict:
        @retry(
            stop=stop_after_attempt(self._max_retries),
            wait=wait_exponential(multiplier=1, min=2, max=20),
            reraise=True,
        )
        def _do_call() -> dict:
            client = self._get_client()
            response = client.models.generate_content(model=self._model, contents=prompt)
            payload = (response.text or "").strip()
            payload = _CODE_FENCE_RE.sub("", payload).strip()
            try:
                return json.loads(payload)
            except json.JSONDecodeError as exc:
                raise AIProviderError(
                    f"Respuesta de Gemini no es JSON válido: {exc}"
                ) from exc

        return _do_call()
