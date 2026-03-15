#!/usr/bin/env python3
"""
main.py
───────
Punto de entrada del Monitor de Precios de Acciones y ETFs.

Uso
───
    python main.py            # inicia el bucle del planificador (por defecto)
    python main.py --una-vez  # ejecuta un solo ciclo de comprobación y sale

Variables de entorno
────────────────────
    RUTA_BD   ruta al fichero de base de datos SQLite  (por defecto: /data/monitor.db)
"""

import argparse
import sys

from database import inicializar_bd
from alerts import ejecutar_comprobacion
from scheduler import ejecutar_planificador



def parsear_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monitor de precios de acciones y ETFs",
    )
    parser.add_argument(
        "--una-vez",
        action="store_true",
        help="Ejecuta un solo ciclo de comprobación y sale (útil para trabajos cron)",
    )
    return parser.parse_args()



def main() -> None:
    args = parsear_argumentos()
    inicializar_bd()

    if args.una_vez:
        ejecutar_comprobacion()
        sys.exit(0)
    else:
        ejecutar_planificador()



if __name__ == "__main__":
    main()
