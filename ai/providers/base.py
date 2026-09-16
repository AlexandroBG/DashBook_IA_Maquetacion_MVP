"""
ai/providers/base.py — Contrato que debe cumplir cualquier proveedor de IA.

El resto del proyecto (structure_detector, front_matter) solo conoce
esta interfaz, nunca el SDK concreto de un proveedor. Añadir un
proveedor nuevo (OpenAI, Claude, Vertex AI...) consiste en:

    1. Crear ai/providers/<nombre>.py con una clase que implemente
       AIProvider.
    2. Registrarla en el diccionario _PROVIDERS de ai/client.py.
    3. Seleccionarla con AI_PROVIDER=<nombre> en el .env.

Ningún otro módulo del proyecto necesita cambios.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Proveedor de IA capaz de devolver una respuesta JSON a partir de
    un prompt de texto. Es el único método que necesita este proyecto:
    tanto la detección de capítulos por IA como la generación de front
    matter piden siempre una respuesta JSON estructurada.
    """

    @abstractmethod
    def generate_json(self, prompt: str) -> dict:
        """Envía `prompt` al modelo y devuelve la respuesta ya parseada
        como dict.

        El proveedor es responsable de: pedir JSON al modelo, limpiar
        posibles backticks de Markdown en la respuesta, parsear el JSON
        y reintentar ante errores transitorios (rate limit, 5xx).

        Debe lanzar `core.errors.AIProviderError` si no consigue una
        respuesta JSON válida tras agotar los reintentos configurados.
        """
        raise NotImplementedError
