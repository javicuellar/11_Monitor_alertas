"""
admin/db.py
───────────
Acceso a la base de datos SQLite compartido por todas las páginas del panel.
Solo este módulo toca sqlite3 directamente.
"""

import os
import sqlite3



RUTA_BD: str = os.environ.get("RUTA_BD",
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "monitor.db"),)



def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(RUTA_BD)
    c.row_factory = sqlite3.Row
    return c


def ejecutar(sql: str, params: tuple = ()) -> None:
    """Ejecuta una sentencia SQL de escritura (INSERT / UPDATE / DELETE)."""
    with _conn() as c:
        c.execute(sql, params)


def consultar(sql: str, params: tuple = ()) -> list[dict]:
    """Ejecuta una consulta SELECT y devuelve una lista de dicts."""
    with _conn() as c:
        rows = c.execute(sql, params).fetchall()
    return [dict(r) for r in rows]
