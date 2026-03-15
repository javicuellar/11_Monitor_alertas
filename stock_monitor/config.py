"""
config.py
─────────
Constantes globales y configuración de logging compartidas por todos los módulos.
"""

import logging
import os
import sys


# ── Ruta de la base de datos ───────────────────────────────────────────────────
RUTA_BD: str = os.environ.get("RUTA_BD", "/data/monitor.db")

# Alias para mantener compatibilidad si se usa la variable de entorno DB_PATH
DB_PATH = RUTA_BD


# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


def obtener_logger(nombre: str) -> logging.Logger:
    """Devuelve un logger a nivel de módulo con un formato consistente."""
    return logging.getLogger(nombre)
