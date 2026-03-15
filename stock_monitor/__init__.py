"""
monitor_acciones
────────────────
Paquete del monitor de precios de acciones y ETFs.

Re-exportaciones públicas para importaciones cómodas en una sola línea:

    from stock_monitor import ejecutar_planificador, ejecutar_comprobacion
"""

from .alerts import ejecutar_comprobacion
from .database import inicializar_bd
from .scheduler import ejecutar_planificador


__all__ = ["inicializar_bd", "ejecutar_comprobacion", "ejecutar_planificador"]
