"""
admin/pagina_dashboard.py
─────────────────────────
Pantalla: Panel de Control.
Muestra métricas generales, estado de los servicios y las últimas alertas.
"""

import pandas as pd
import streamlit as st

from .db import RUTA_BD, consultar
from .ui import card, seccion


def render() -> None:
    st.title("📊 Panel de Control")

    # ── Métricas ──────────────────────────────────────────────────────────────
    try:
        n_activos     = consultar("SELECT COUNT(*) as n FROM simbolos WHERE activo=1")[0]["n"]
        n_total_sim   = consultar("SELECT COUNT(*) as n FROM simbolos")[0]["n"]
        alertas_hoy   = consultar("SELECT COUNT(*) as n FROM historial_alertas WHERE fecha_alerta=date('now')")[0]["n"]
        total_alertas = consultar("SELECT COUNT(*) as n FROM historial_alertas")[0]["n"]
        email_ok      = consultar("SELECT COUNT(*) as n FROM configuracion_email WHERE activo=1")[0]["n"]
        tg_ok         = consultar("SELECT COUNT(*) as n FROM configuracion_telegram WHERE activo=1")[0]["n"]
    except Exception as e:
        st.error(f"No se pudo conectar a la base de datos: {e}")
        st.info(f"Ruta configurada: `{RUTA_BD}`")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Símbolos activos",  f"{n_activos} / {n_total_sim}")
    c2.metric("Alertas hoy",       alertas_hoy)
    c3.metric("Total alertas",     total_alertas)
    c4.metric(
        "Notificaciones",
        f"{'✅' if email_ok else '❌'} Email  {'✅' if tg_ok else '❌'} TG",
    )

    # ── Estado de servicios ───────────────────────────────────────────────────
    seccion("Estado de servicios")
    col_e, col_t, col_p = st.columns(3)

    cfg_email = consultar("SELECT * FROM configuracion_email LIMIT 1")
    col_e.markdown(
        f"""<div class="card card-{'verde' if email_ok else 'rojo'}">
        <div style="font-size:0.75rem;color:#6b7a8d;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;">Email SMTP</div>
        <div style="font-size:1rem;font-weight:600;color:#1a2332;">{'✅ Activo' if email_ok else '❌ Inactivo'}</div>
        {f'<div style="font-size:0.8rem;color:#6b7a8d;margin-top:4px;">{cfg_email[0]["servidor_smtp"]}:{cfg_email[0]["puerto_smtp"]}</div>' if cfg_email else ''}
        </div>""",
        unsafe_allow_html=True,
    )

    cfg_tg = consultar("SELECT * FROM configuracion_telegram LIMIT 1")
    col_t.markdown(
        f"""<div class="card card-{'verde' if tg_ok else 'rojo'}">
        <div style="font-size:0.75rem;color:#6b7a8d;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;">Telegram Bot</div>
        <div style="font-size:1rem;font-weight:600;color:#1a2332;">{'✅ Activo' if tg_ok else '❌ Inactivo'}</div>
        {f'<div style="font-size:0.8rem;color:#6b7a8d;margin-top:4px;">Chat: {cfg_tg[0]["id_chat"]}</div>' if cfg_tg else ''}
        </div>""",
        unsafe_allow_html=True,
    )

    cfg_plan = consultar("SELECT * FROM configuracion_planificador LIMIT 1")
    if cfg_plan:
        p = cfg_plan[0]
        col_p.markdown(
            f"""<div class="card card-azul">
            <div style="font-size:0.75rem;color:#6b7a8d;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;">Planificador</div>
            <div style="font-size:1rem;font-weight:600;color:#1a2332;">⏱ Cada {p['intervalo_minutos']} min</div>
            <div style="font-size:0.8rem;color:#6b7a8d;margin-top:4px;">{p['hora_inicio']} – {p['hora_fin']} · {'Solo laborables' if p['solo_laborables'] else 'Todos los días'}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    # ── Últimas alertas ───────────────────────────────────────────────────────
    seccion("Últimas 20 alertas")
    alertas = consultar("""
        SELECT ticker, fecha_alerta,
               ROUND(cierre_anterior,2)   AS cierre,
               ROUND(precio_actual,2)     AS precio,
               ROUND(cambio_porcentaje,2) AS cambio,
               direccion,
               CASE WHEN notificado_email=1    THEN '✅' ELSE '❌' END AS email,
               CASE WHEN notificado_telegram=1 THEN '✅' ELSE '❌' END AS tg,
               creado_en
        FROM historial_alertas ORDER BY creado_en DESC LIMIT 20
    """)
    if alertas:
        df = pd.DataFrame(alertas)
        df.columns = ["Ticker", "Fecha", "Cierre ant.", "Precio act.", "Cambio %", "Dir.", "Email", "TG", "Creado"]
        st.dataframe(df, hide_index=True)
    else:
        st.info("Todavía no hay alertas registradas.")

    # ── Símbolos monitorizados ────────────────────────────────────────────────
    seccion("Símbolos monitorizados")
    sims = consultar("SELECT ticker, nombre, umbral, activo FROM simbolos ORDER BY ticker")
    if sims:
        df2 = pd.DataFrame(sims)
        df2["activo"] = df2["activo"].apply(lambda x: "🟢 Activo" if x else "🔴 Inactivo")
        df2.columns   = ["Ticker", "Nombre", "Umbral %", "Estado"]
        st.dataframe(df2, hide_index=True)
