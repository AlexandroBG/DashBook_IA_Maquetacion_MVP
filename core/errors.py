"""
core/errors.py — Excepciones de negocio del pipeline.

Se usan para errores que el usuario final debe entender tal cual
(manuscrito vacío, idioma no soportado, API key ausente, etc.), a
diferencia de tracebacks internos inesperados que deben quedar en el log.
"""

from __future__ import annotations


class PipelineError(Exception):
    """Error de negocio genérico del pipeline."""


class AIProviderError(PipelineError):
    """Error específico de la capa de IA: conexión, cuota, JSON inválido,
    proveedor no soportado, etc. Se distingue de PipelineError para que
    la UI pueda mostrar un mensaje más preciso ("problema con el
    proveedor de IA" vs "problema con el manuscrito").
    """
