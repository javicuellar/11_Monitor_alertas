"""
admin/pagina_historial.py
─────────────────────────
Pantalla: Historial de Alertas.
Consulta filtrada del historial con opción de limpieza completa.
"""

import pandas as pd
import streamlit as st

from .db import consultar, ejecutar
from .ui import seccion


def _tabla_alertas(alertas: list[dict]) -> None:
    """Renderiza el DataFrame del historial con columnas formateadas."""
    df = pd.DataFrame(alertas)
    df["notificado_email"]    = df["notificado_email"].map({1: "✅", 0: "❌"})
    df["notificado_telegram"] = df["notificado_telegram"].map({1: "✅", 0: "❌"})
    df["cambio_porcentaje"]   = df["cambio_porcentaje"].apply(lambda x: f"{x:+.2f}%")
    df = df.drop(columns=["id"])
    df.columns = ["Ticker", "Fecha", "Cierre ant.", "Precio act.", "Cambio", "Dir.", "Email", "TG", "Creado"]
    st.dataframe(df, hide_index=True)


def _panel_limpieza() -> None:
    """Renderiza la zona de peligro con confirmación de borrado."""
    st.markdown("---")
    seccion("⚠️ Zona peligrosa")
    col1, _ = st.columns([1, 3])
    with col1:
        st.markdown('<div class="btn-peligro">', unsafe_allow_html=True)
        if st.button("🗑 Limpiar historial completo"):
            st.session_state["confirmar_limpieza"] = True
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.get("confirmar_limpieza"):
        st.warning(
            "¿Estás seguro? Esta acción eliminará **todos** los registros "
            "del historial y no se puede deshacer."
        )
        cc1, cc2, _ = st.columns([1, 1, 2])
        if cc1.button("✅ Sí, borrar todo"):
            ejecutar("DELETE FROM historial_alertas")
            st.session_state["confirmar_limpieza"] = False
            st.success("Historial eliminado correctamente.")
            st.rerun()
        if cc2.button("❌ Cancelar"):
            st.session_state["confirmar_limpieza"] = False
            st.rerun()


def render() -> None:
    st.title("📜 Historial de Alertas")

    # ── Filtros ───────────────────────────────────────────────────────────────
    seccion("Filtros")
    c1, c2, c3 = st.columns(3)

    tickers_bd = [
        r["ticker"]
        for r in consultar("SELECT DISTINCT ticker FROM historial_alertas ORDER BY ticker")
    ]
    filtro_ticker = c1.selectbox("Ticker",    ["Todos"] + tickers_bd)
    filtro_dir    = c2.selectbox("Dirección", ["Todas", "▲ SUBE", "▼ BAJA"])
    filtro_n      = c3.number_input("Últimos N registros", value=50, min_value=1, max_value=1000)

    # ── Construcción dinámica de la query ─────────────────────────────────────
    where, params = [], []
    if filtro_ticker != "Todos":
        where.append("ticker=?");    params.append(filtro_ticker)
    if filtro_dir != "Todas":
        where.append("direccion=?"); params.append(filtro_dir)

    sql = "SELECT * FROM historial_alertas"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY creado_en DESC LIMIT {int(filtro_n)}"

    alertas = consultar(sql, tuple(params))

    # ── Resultados ────────────────────────────────────────────────────────────
    if not alertas:
        st.info("No hay alertas con los filtros seleccionados.")
    else:
        seccion(f"{len(alertas)} registros encontrados")
        _tabla_alertas(alertas)

    _panel_limpieza()
