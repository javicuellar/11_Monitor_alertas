"""
scheduler.py
────────────
Control de ventana horaria y bucle principal del planificador.

El bucle relee `configuracion_planificador` desde la BD en cada iteración,
por lo que cualquier cambio realizado mientras el proceso está en marcha
surte efecto en el siguiente ciclo — sin necesidad de reiniciar.

Columnas de configuracion_planificador
───────────────────────────────────────
intervalo_minutos – cada cuántos minutos ejecutar un ciclo      (por defecto 30)
hora_inicio       – hora de inicio permitida más temprana HH:MM  (por defecto 09:00)
hora_fin          – hora de inicio permitida más tardía  HH:MM  (por defecto 22:00)
solo_laborables   – 1 = omitir sáb y dom, 0 = ejecutar todos los días (por defecto 1)
"""

import time
from datetime import datetime

from .alerts import ejecutar_comprobacion
from .config import obtener_logger
from .database import obtener_config_planificador



log = obtener_logger(__name__)


# ── Funciones auxiliares ──────────────────────────────────────────────────────

def _parsear_hhmm(hhmm: str) -> tuple[int, int]:
    """Convierte una cadena 'HH:MM' en una tupla (hora, minuto) de enteros."""
    h, m = hhmm.strip().split(":")
    return int(h), int(m)


def esta_en_ventana_activa(cfg: dict) -> bool:
    """
    Devuelve True si el momento actual está dentro de la ventana de comprobación configurada.

    Comprueba:
      - Restricción de día laborable (solo_laborables=1 omite sábado=5 y domingo=6)
      - Ventana horaria del día [hora_inicio, hora_fin] inclusive
    """
    ahora = datetime.now()

    if cfg["solo_laborables"] and ahora.weekday() >= 5:
        return False

    inicio_h, inicio_m = _parsear_hhmm(cfg["hora_inicio"])
    fin_h,    fin_m    = _parsear_hhmm(cfg["hora_fin"])

    inicio_dt = ahora.replace(hour=inicio_h, minute=inicio_m, second=0, microsecond=0)
    fin_dt    = ahora.replace(hour=fin_h,    minute=fin_m,    second=0, microsecond=0)

    return inicio_dt <= ahora <= fin_dt


# ── Bucle principal ───────────────────────────────────────────────────────────

def ejecutar_planificador() -> None:
    """
    Bucle infinito que ejecuta ejecutar_comprobacion() cuando el momento actual
    está dentro de la ventana activa configurada.

    La configuración se recarga desde la BD en cada iteración.
    """
    log.info("=== Planificador arrancado ===")

    while True:
        cfg               = obtener_config_planificador()
        segundos_intervalo = cfg["intervalo_minutos"] * 60

        if esta_en_ventana_activa(cfg):
            try:
                ejecutar_comprobacion()
            except Exception as exc:
                log.error("Error inesperado en ejecutar_comprobacion: %s", exc)
        else:
            log.info(
                "Fuera de ventana horaria (%s–%s, solo_laborables=%s). "
                "Próximo ciclo en %d min.",
                cfg["hora_inicio"], cfg["hora_fin"],
                cfg["solo_laborables"], cfg["intervalo_minutos"],
            )

        log.info("Durmiendo %d minutos…", cfg["intervalo_minutos"])
        time.sleep(segundos_intervalo)
