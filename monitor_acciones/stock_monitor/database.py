"""
database.py
───────────
Conexión SQLite, inicialización del esquema y todas las funciones de acceso a datos.

Todos los demás módulos importan desde aquí — ninguno toca sqlite3 directamente.
"""

import sqlite3
from typing import Optional

from .config import RUTA_BD, obtener_logger




log = obtener_logger(__name__)


# ── Conexión ──────────────────────────────────────────────────────────────────

def obtener_conexion() -> sqlite3.Connection:
    """Devuelve una conexión a la base de datos SQLite."""
    try:
        conn = sqlite3.connect(RUTA_BD)
    except sqlite3.Error as exc:
        log.error("Error al conectar con la base de datos: %s", exc)
        exit(1)
    conn.row_factory = sqlite3.Row
    return conn


# ── Esquema ───────────────────────────────────────────────────────────────────

_ESQUEMA = """
-- Configuración del email
CREATE TABLE IF NOT EXISTS configuracion_email (
    id                INTEGER PRIMARY KEY,
    servidor_smtp     TEXT    NOT NULL,
    puerto_smtp       INTEGER NOT NULL DEFAULT 587,
    usuario           TEXT    NOT NULL,
    password          TEXT    NOT NULL,
    direccion_origen  TEXT   NOT NULL,
    direccion_destino TEXT  NOT NULL,
    activo            INTEGER NOT NULL DEFAULT 1
);

-- Configuración de Telegram
CREATE TABLE IF NOT EXISTS configuracion_telegram (
    id              INTEGER PRIMARY KEY,
    token_bot       TEXT NOT NULL,
    id_chat         TEXT NOT NULL,
    activo          INTEGER NOT NULL DEFAULT 1
);


-- Configuración del planificador
--   intervalo_minutos : minutos entre cada comprobación de precios
--   hora_inicio       : hora más temprana para ejecutar (HH:MM, 24 h)
--   hora_fin          : hora más tardía para ejecutar   (HH:MM, 24 h)
--   solo_laborables   : 1 = saltar sábado y domingo, 0 = ejecutar todos los días
CREATE TABLE IF NOT EXISTS configuracion_planificador (
    id                  INTEGER PRIMARY KEY,
    intervalo_minutos   INTEGER NOT NULL DEFAULT 30,
    hora_inicio         TEXT    NOT NULL DEFAULT '09:00',
    hora_fin            TEXT    NOT NULL DEFAULT '22:00',
    solo_laborables     INTEGER NOT NULL DEFAULT 1
);

-- Símbolos a monitorizar
CREATE TABLE IF NOT EXISTS simbolos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker      TEXT    NOT NULL UNIQUE,
    nombre      TEXT,
    umbral      REAL    NOT NULL DEFAULT 2.0,
    activo      INTEGER NOT NULL DEFAULT 1
);

-- Historial de alertas
CREATE TABLE IF NOT EXISTS historial_alertas (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker              TEXT NOT NULL,
    fecha_alerta        TEXT NOT NULL,
    cierre_anterior     REAL,
    precio_actual       REAL,
    cambio_porcentaje   REAL,
    direccion           TEXT,
    notificado_email    INTEGER DEFAULT 0,
    notificado_telegram INTEGER DEFAULT 0,
    creado_en           TEXT DEFAULT (datetime('now'))
);
"""

_SIMBOLOS_INICIALES = [
    ("SPY",  "SPDR S&P 500 ETF",  2.0),
    ("QQQ",  "Invesco QQQ ETF",   2.0),
    ("AAPL", "Apple Inc.",        2.0),
    ("MSFT", "Microsoft Corp.",   2.0),
    ("NVDA", "NVIDIA Corp.",      2.0),
]



def inicializar_bd() -> None:
    """Crea las tablas (si no existen) y rellena los datos iniciales por defecto."""
    with obtener_conexion() as conn:
        conn.executescript(_ESQUEMA)

        if not conn.execute("SELECT 1 FROM configuracion_planificador LIMIT 1").fetchone():
            conn.execute(
                "INSERT INTO configuracion_planificador "
                "(intervalo_minutos, hora_inicio, hora_fin, solo_laborables) "
                "VALUES (30, '09:00', '22:00', 1)"
            )

        if not conn.execute("SELECT 1 FROM configuracion_email LIMIT 1").fetchone():
            conn.execute(
                "INSERT INTO configuracion_email "
                "(servidor_smtp, puerto_smtp, usuario, password, "
                " direccion_origen, direccion_destino, activo) "
                "VALUES ('smtp.gmail.com', 587, 'tu@gmail.com', 'tu_password_app', "
                "        'tu@gmail.com', 'destinatario@email.com', 0)"
            )

        if not conn.execute("SELECT 1 FROM configuracion_telegram LIMIT 1").fetchone():
            conn.execute(
                "INSERT INTO configuracion_telegram (token_bot, id_chat, activo) "
                "VALUES ('TU_TOKEN_BOT', 'TU_ID_CHAT', 0)"
            )

        if not conn.execute("SELECT 1 FROM simbolos LIMIT 1").fetchone():
            for ticker, nombre, umbral in _SIMBOLOS_INICIALES:
                conn.execute(
                    "INSERT OR IGNORE INTO simbolos (ticker, nombre, umbral) VALUES (?,?,?)",
                    (ticker, nombre, umbral),
                )

    log.info("Base de datos inicializada en %s", RUTA_BD)



# ── Configuración del planificador ────────────────────────────────────────────

def obtener_config_planificador() -> dict:
    """Devuelve la configuración del planificador desde la BD (con valores por defecto si falta)."""
    with obtener_conexion() as conn:
        fila = conn.execute("SELECT * FROM configuracion_planificador LIMIT 1").fetchone()
    if fila:
        return {
            "intervalo_minutos": int(fila["intervalo_minutos"]),
            "hora_inicio":       fila["hora_inicio"],
            "hora_fin":          fila["hora_fin"],
            "solo_laborables":   bool(fila["solo_laborables"]),
        }
    return {
        "intervalo_minutos": 30,
        "hora_inicio": "09:00",
        "hora_fin": "22:00",
        "solo_laborables": True,
    }



# ── Configuraciones de notificación ──────────────────────────────────────────

def obtener_config_email() -> Optional[sqlite3.Row]:
    """Devuelve la configuración de email activa, o None si no existe."""
    with obtener_conexion() as conn:
        return conn.execute(
            "SELECT * FROM configuracion_email WHERE activo=1 LIMIT 1"
        ).fetchone()



def obtener_config_telegram() -> Optional[sqlite3.Row]:
    """Devuelve la configuración de Telegram activa, o None si no existe."""
    with obtener_conexion() as conn:
        return conn.execute(
            "SELECT * FROM configuracion_telegram WHERE activo=1 LIMIT 1"
        ).fetchone()




# ── Símbolos ──────────────────────────────────────────────────────────────────

def obtener_simbolos_activos() -> list[sqlite3.Row]:
    """Devuelve todos los símbolos con activo=1."""
    with obtener_conexion() as conn:
        return conn.execute(
            "SELECT ticker, nombre, umbral FROM simbolos WHERE activo=1"
        ).fetchall()



# ── Historial de alertas ──────────────────────────────────────────────────────

def ya_alertado(ticker: str, fecha_alerta: str) -> bool:
    """Devuelve True si ya se registró una alerta para este ticker hoy."""
    with obtener_conexion() as conn:
        fila = conn.execute(
            "SELECT id FROM historial_alertas WHERE ticker=? AND fecha_alerta=?",
            (ticker, fecha_alerta),
        ).fetchone()
    return fila is not None



def guardar_alerta(datos: dict, notificado_email: bool, notificado_telegram: bool) -> None:
    """Persiste una alerta disparada en la tabla de historial."""
    with obtener_conexion() as conn:
        conn.execute(
            "INSERT INTO historial_alertas "
            "(ticker, fecha_alerta, cierre_anterior, precio_actual, cambio_porcentaje, "
            " direccion, notificado_email, notificado_telegram) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                datos["ticker"],           datos["fecha"],
                datos["cierre_anterior"],  datos["precio_actual"],
                datos["cambio_porcentaje"], datos["direccion"],
                int(notificado_email),     int(notificado_telegram),
            ),
        )
