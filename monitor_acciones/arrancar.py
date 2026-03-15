#!/usr/bin/env python3
"""
arrancar.py
───────────
Script de arranque que lanza simultáneamente:
  1. El monitor de acciones (planificador de alertas) — en un hilo secundario
  2. La aplicación web Streamlit de administración   — en el proceso principal

Uso:
    python arrancar.py                    # lanza ambos servicios
    python arrancar.py --solo-monitor     # solo el planificador (sin UI)
    python arrancar.py --solo-admin       # solo la UI de administración (sin monitor)
    python arrancar.py --una-vez          # ejecuta un solo ciclo del monitor y sale

Variables de entorno:
    RUTA_BD         ruta al fichero SQLite   (por defecto: ./data/monitor.db)
    ADMIN_PUERTO    puerto de Streamlit      (por defecto: 8501)
"""

import argparse
import os
import subprocess
import sys
import threading
import time
import signal



# ── Aseguramos que el paquete stock_monitor sea importable ────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)


# ── Crear directorio de datos si no existe ────────────────────────────────────
RUTA_BD_DEFAULT = os.path.join(BASE_DIR, "data", "monitor.db")
RUTA_BD = os.environ.get("RUTA_BD", RUTA_BD_DEFAULT)
os.makedirs(os.path.dirname(RUTA_BD), exist_ok=True)
os.environ["RUTA_BD"] = RUTA_BD      # propagamos a subprocesos



# ══════════════════════════════════════════════════════════════════════════════
# MONITOR DE ACCIONES
# ══════════════════════════════════════════════════════════════════════════════

def _hilo_monitor(modo_una_vez: bool) -> None:
    """Ejecuta el planificador (o un solo ciclo) dentro de un hilo."""
    # try:
    if True:
        # Importamos aquí para que el path ya esté configurado
        from stock_monitor.database import inicializar_bd
        from stock_monitor.alerts import ejecutar_comprobacion
        from stock_monitor.scheduler import ejecutar_planificador

    try:
        inicializar_bd()

        if modo_una_vez:
            print("[MONITOR] Ejecutando ciclo único…")
            ejecutar_comprobacion()
            print("[MONITOR] Ciclo completado.")
        else:
            print("[MONITOR] Planificador arrancado.")
            ejecutar_planificador()          # bucle infinito

    except Exception as exc:
        print(f"[MONITOR] Error fatal: {exc}", file=sys.stderr)


def arrancar_monitor(modo_una_vez: bool = False) -> threading.Thread:
    """Lanza el monitor en un hilo daemon y lo devuelve."""
    hilo = threading.Thread(
        target=_hilo_monitor,
        args=(modo_una_vez,),
        name="monitor-acciones",
        daemon=True,          # muere cuando muere el proceso principal
    )
    hilo.start()
    return hilo




# ══════════════════════════════════════════════════════════════════════════════
# APLICACIÓN STREAMLIT
# ══════════════════════════════════════════════════════════════════════════════

def arrancar_admin(puerto: int = 8501) -> subprocess.Popen:
    """
    Lanza la app Streamlit como subproceso y devuelve el objeto Popen.
    El subproceso se termina automáticamente al salir del proceso principal.
    """
    ruta_app = os.path.join(BASE_DIR, "admin_app.py")
    cmd = [
        sys.executable, "-m", "streamlit", "run", ruta_app,
        "--server.port",        str(puerto),
        "--server.headless",    "true",
        "--server.address",     "0.0.0.0",
        "--browser.gatherUsageStats", "false",
    ]
    proceso = subprocess.Popen(
        cmd,
        env={**os.environ},   # hereda RUTA_BD y resto de variables
    )
    return proceso




# ══════════════════════════════════════════════════════════════════════════════
# ARGUMENTOS Y PUNTO DE ENTRADA
# ══════════════════════════════════════════════════════════════════════════════

def parsear_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monitor de Acciones + Panel de Administración",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--solo-monitor", action="store_true",
                        help="Lanza solo el planificador de alertas (sin UI)")
    parser.add_argument("--solo-admin",   action="store_true",
                        help="Lanza solo la UI de administración Streamlit (sin monitor)")
    parser.add_argument("--una-vez",      action="store_true",
                        help="Ejecuta un solo ciclo del monitor y sale")
    parser.add_argument("--puerto",       type=int, default=int(os.environ.get("ADMIN_PUERTO", 8501)),
                        help="Puerto para la aplicación Streamlit (por defecto: 8501)")
    return parser.parse_args()


def main() -> None:
    args = parsear_argumentos()
    proc_admin  = None
    hilo_monitor = None

    # ── Manejador de señales para apagado limpio ──────────────────────────────
    def apagar(sig, frame):
        print("\n[ARRANCAR] Apagando servicios…")
        if proc_admin and proc_admin.poll() is None:
            proc_admin.terminate()
            proc_admin.wait(timeout=5)
            print("[ARRANCAR] Panel de administración detenido.")
        print("[ARRANCAR] Saliendo.")
        sys.exit(0)

    signal.signal(signal.SIGINT,  apagar)
    signal.signal(signal.SIGTERM, apagar)

    # ── Modo: solo monitor ────────────────────────────────────────────────────
    if args.solo_monitor or args.una_vez:
        from stock_monitor.database import inicializar_bd
        from stock_monitor.alerts import ejecutar_comprobacion
        from stock_monitor.scheduler import ejecutar_planificador
        inicializar_bd()
        if args.una_vez:
            ejecutar_comprobacion()
        else:
            ejecutar_planificador()
        return

    # ── Modo: solo admin ──────────────────────────────────────────────────────
    if args.solo_admin:
        proc_admin = arrancar_admin(args.puerto)
        print(f"[ARRANCAR] Panel de administración en http://localhost:{args.puerto}")
        proc_admin.wait()
        return

    # ── Modo completo: monitor + admin ────────────────────────────────────────
    print("=" * 60)
    print("  MONITOR DE ACCIONES + PANEL DE ADMINISTRACIÓN")
    print("=" * 60)
    print(f"  Base de datos : {RUTA_BD}")
    print(f"  Panel admin   : http://localhost:{args.puerto}")
    print("  (Ctrl+C para detener ambos servicios)")
    print("=" * 60)

    # 1. Lanzar monitor en hilo secundario
    hilo_monitor = arrancar_monitor(modo_una_vez=False)
    print("[ARRANCAR] ✅ Monitor de acciones arrancado en segundo plano.")

    # Pequeña pausa para que el monitor inicialice la BD antes que Streamlit la abra
    time.sleep(2)

    # 2. Lanzar Streamlit en subproceso (bloquea hasta que se cierra)
    proc_admin = arrancar_admin(args.puerto)
    print(f"[ARRANCAR] ✅ Panel de administración en http://localhost:{args.puerto}")

    # Esperar a que Streamlit termine (o a Ctrl+C)
    try:
        proc_admin.wait()
    except KeyboardInterrupt:
        apagar(None, None)




if __name__ == "__main__":
    main()
