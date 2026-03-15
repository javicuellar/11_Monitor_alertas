"""
admin/pagina_planificador.py
────────────────────────────
Pantalla: Planificador.
Permite configurar el intervalo, ventana horaria y días de ejecución.
"""

import re
import streamlit as st

from .db import consultar, ejecutar
from .ui import card, seccion


def render() -> None:
    st.title("⏱ Planificador")

    filas = consultar("SELECT * FROM configuracion_planificador LIMIT 1")
    if not filas:
        st.error("No hay configuración del planificador en la base de datos.")
        return

    cfg = filas[0]

    # ── Formulario de edición ─────────────────────────────────────────────────
    seccion("Parámetros de ejecución")
    with st.form("form_planificador"):
        c1, c2 = st.columns(2)
        intervalo   = c1.number_input(
            "Intervalo entre comprobaciones (minutos)",
            min_value=1, max_value=1440, value=int(cfg["intervalo_minutos"]),
        )
        solo_lab = c2.checkbox(
            "Solo días laborables (Lunes a Viernes)",
            value=bool(cfg["solo_laborables"]),
        )
        c3, c4 = st.columns(2)
        hora_inicio = c3.text_input("Hora de inicio (HH:MM)", value=cfg["hora_inicio"])
        hora_fin    = c4.text_input("Hora de fin (HH:MM)",    value=cfg["hora_fin"])

        st.markdown('<div class="btn-primario">', unsafe_allow_html=True)
        guardado = st.form_submit_button("💾 Guardar cambios")
        st.markdown('</div>', unsafe_allow_html=True)

        if guardado:
            patron = r"^\d{2}:\d{2}$"
            if not re.match(patron, hora_inicio) or not re.match(patron, hora_fin):
                st.error("Formato de hora incorrecto. Usa HH:MM — por ejemplo: 09:00")
            else:
                ejecutar(
                    "UPDATE configuracion_planificador SET "
                    "intervalo_minutos=?, hora_inicio=?, hora_fin=?, solo_laborables=? WHERE id=?",
                    (intervalo, hora_inicio, hora_fin, int(solo_lab), cfg["id"]),
                )
                st.success("✅ Planificador actualizado. Los cambios surten efecto en el próximo ciclo.")
                st.rerun()

    # ── Resumen visual ────────────────────────────────────────────────────────
    seccion("Resumen de configuración activa")
    dias = "Lunes a Viernes" if cfg["solo_laborables"] else "Todos los días"
    card(
        f"""
        <div style="display:flex;gap:32px;flex-wrap:wrap;align-items:center;">
            <div>
                <span style="font-size:0.72rem;color:#6b7a8d;text-transform:uppercase;letter-spacing:0.08em;">Frecuencia</span>
                <div style="font-size:1.1rem;font-weight:600;color:#1a2332;margin-top:2px;">🔁 Cada {cfg['intervalo_minutos']} min</div>
            </div>
            <div>
                <span style="font-size:0.72rem;color:#6b7a8d;text-transform:uppercase;letter-spacing:0.08em;">Ventana horaria</span>
                <div style="font-size:1.1rem;font-weight:600;color:#1a2332;margin-top:2px;">🕐 {cfg['hora_inicio']} — {cfg['hora_fin']}</div>
            </div>
            <div>
                <span style="font-size:0.72rem;color:#6b7a8d;text-transform:uppercase;letter-spacing:0.08em;">Días activos</span>
                <div style="font-size:1.1rem;font-weight:600;color:#1a2332;margin-top:2px;">📅 {dias}</div>
            </div>
        </div>
        """,
        tipo="azul",
    )
