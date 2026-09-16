"""
ai/client.py — Punto único de entrada del proyecto a la capa de IA.

Ningún módulo de negocio (structure_detector, front_matter) debe
importar un SDK de proveedor directamente ni saber qué proveedor está
activo: todos llaman a `generate_json()` de este módulo.

Cambiar de proveedor o de modelo es, en el caso normal, solo cuestión
de editar AI_PROVIDER / AI_MODEL en el .env (ver config.py y README).
"""

from __future__ import annotations

from functools import lru_cache

from config import AI_API_KEY, AI_MAX_RETRIES, AI_MODEL, AI_PROVIDER
from core.errors import AIProviderError

from .providers.base import AIProvider


def _build_provider() -> AIProvider:
    provider_name = (AI_PROVIDER or "gemini").strip().lower()

    if provider_name == "gemini":
        from .providers.gemini import GeminiProvider

        return GeminiProvider(api_key=AI_API_KEY, model=AI_MODEL, max_retries=AI_MAX_RETRIES)

    # Para añadir un proveedor nuevo: crear ai/providers/<nombre>.py con
    # una clase que implemente AIProvider, e importarla/instanciarla aquí
    # bajo un nuevo `elif provider_name == "<nombre>":`.
    raise AIProviderError(
        f"Proveedor de IA '{provider_name}' no soportado. "
        f"Proveedores disponibles: gemini. "
        f"Añade uno nuevo en ai/providers/ y regístralo en ai/client.py."
    )


@lru_cache(maxsize=1)
def get_ai_provider() -> AIProvider:
    """Devuelve el proveedor de IA activo (instancia única, perezosa)."""
    return _build_provider()


def generate_json(prompt: str, required_fields: set[str] | None = None) -> dict:
    """Pide al proveedor de IA activo una respuesta JSON para `prompt`.

    Si se indica `required_fields`, valida que todos estén presentes en
    la respuesta y lanza AIProviderError si falta alguno — así los
    módulos de negocio no tienen que repetir esa validación.
    """
    provider = get_ai_provider()
    data = provider.generate_json(prompt)

    if required_fields:
        missing = required_fields - data.keys()
        if missing:
            raise AIProviderError(
                f"Faltan campos en la respuesta del proveedor de IA: {missing}"
            )
    return data
