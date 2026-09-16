"""
utils/logging.py — Logging y utilidades transversales del pipeline.
"""

from __future__ import annotations

import contextlib
import logging
import time
from pathlib import Path

from config import LOGS_DIR
from core.errors import PipelineError


def get_logger(name: str) -> logging.Logger:
    """Devuelve un logger configurado con salida a consola y a archivo.

    Idempotente: si el logger ya tiene handlers (por ejemplo, en Streamlit,
    que re-ejecuta el módulo en cada interacción) no los duplica.
    """
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    file_handler = logging.FileHandler(LOGS_DIR / "dashbook.log", encoding="utf-8")
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger


@contextlib.contextmanager
def timer(logger: logging.Logger, label: str, on_step=None):
    """Context manager que mide y loguea la duración de un bloque.

    Si se proporciona `on_step` (callable que acepta un str), se invoca
    al empezar el bloque con el label — pensado para conectar el
    progreso real del pipeline con una barra de estado en la UI, en vez
    de simular pasos fijos.

    Uso:
        with timer(logger, "Extracción de texto", on_step=callback):
            extract(...)
    """
    if on_step is not None:
        on_step(label)
    start = time.perf_counter()
    logger.info("▶ %s...", label)
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        logger.info("✔ %s completado en %.2fs", label, elapsed)


def ensure_within(path: Path, allowed_parent: Path) -> Path:
    """Verifica que `path` esté contenido dentro de `allowed_parent`.

    Defensa básica contra path traversal al construir rutas de salida
    a partir de nombres de archivo proporcionados por el usuario.
    """
    resolved = path.resolve()
    if allowed_parent.resolve() not in resolved.parents and resolved != allowed_parent.resolve():
        raise PipelineError(f"Ruta fuera del directorio permitido: {path}")
    return resolved
