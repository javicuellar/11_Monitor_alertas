"""
admin/pagina_simbolos.py
────────────────────────
Pantalla: Símbolos.
CRUD completo sobre la tabla `simbolos`: listar, editar, activar/desactivar
y eliminar símbolos, además de añadir nuevos.
"""

import sqlite3
import streamlit as st

from .db import consultar, ejecutar
from .ui import badge, seccion




def _fila_simbolo(sim: dict) -> None:
    """Renderiza el expander con formulario de edición/eliminación de un símbolo."""
    tipo_badge = "verde" if sim["activo"] else "rojo"
    etiqueta   = "ACTIVO" if sim["activo"] else "INACTIVO"

    with st.expander(f"{sim['ticker']}  —  {sim['nombre'] or '—'}", expanded=False):
        st.markdown(
            f'<div style="margin-bottom:12px;">{badge(etiqueta, tipo_badge)}</div>',
            unsafe_allow_html=True,
        )
        with st.form(f"form_sim_{sim['id']}"):
            # c1, c2   = st.columns([2, 1])
            c1, c2, c3 = st.columns([2, 3, 1])
            ticker_e = c1.text_input("Ticker",  value=sim["ticker"],     key=f"tk_{sim['id']}")
            nombre_e = c2.text_input("Nombre descriptivo", value=sim["nombre"] or "", key=f"nm_{sim['id']}")
            umbral_e = c3.number_input(
                "Umbral de alerta (%)",
                value=float(sim["umbral"]),
                min_value=0.1, max_value=100.0, step=0.1,
                key=f"ub_{sim['id']}",
            )
            activo_e = st.checkbox("Activo", value=bool(sim["activo"]), key=f"ac_{sim['id']}")

            cg, cd = st.columns([2, 1])
            with cg:
                st.markdown('<div class="btn-primario">', unsafe_allow_html=True)
                actualizar = st.form_submit_button("💾 Guardar cambios")
                st.markdown('</div>', unsafe_allow_html=True)
            with cd:
                st.markdown('<div class="btn-peligro">', unsafe_allow_html=True)
                eliminar = st.form_submit_button("🗑 Eliminar")
                st.markdown('</div>', unsafe_allow_html=True)

            if actualizar:
                ejecutar("UPDATE simbolos SET ticker=?, nombre=?, umbral=?, activo=? WHERE id=?",
                    (ticker_e.strip().upper(), nombre_e.strip(), umbral_e, int(activo_e), sim["id"]), )    # type: ignore
                st.success(f"✅ {ticker_e.upper()} actualizado.")      # type: ignore
                st.rerun()
            if eliminar:
                ejecutar("DELETE FROM simbolos WHERE id=?", (sim["id"],))
                st.success(f"🗑 {sim['ticker']} eliminado.")
                st.rerun()



def _form_nuevo_simbolo() -> None:
    """Renderiza el formulario para añadir un nuevo símbolo."""
    with st.form("form_nuevo_sim"):
        c1, c2, c3 = st.columns([2, 3, 1])
        n_ticker = c1.text_input("Ticker (ej: AAPL, SPY, NVDA)")
        n_nombre = c2.text_input("Nombre descriptivo")
        n_umbral = c3.number_input("Umbral %", value=2.0, min_value=0.1, max_value=100.0, step=0.1)
        n_activo = st.checkbox("Activar inmediatamente", value=True)

        st.markdown('<div class="btn-primario">', unsafe_allow_html=True)
        anadir = st.form_submit_button("➕ Añadir símbolo")
        st.markdown('</div>', unsafe_allow_html=True)

        if anadir:
            if not n_ticker.strip():
                st.error("El ticker no puede estar vacío.")
            else:
                try:
                    ejecutar(
                        "INSERT INTO simbolos (ticker, nombre, umbral, activo) VALUES (?,?,?,?)",
                        (n_ticker.strip().upper(), n_nombre.strip(), n_umbral, int(n_activo)),
                    )
                    st.success(f"✅ {n_ticker.upper()} añadido.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error(f"❌ El ticker {n_ticker.upper()} ya existe.")



def render() -> None:
    st.title("📈 Símbolos")

    seccion("Símbolos registrados")
    simbolos = consultar("SELECT id, ticker, nombre, umbral, activo FROM simbolos ORDER BY ticker")
    if simbolos:
        for sim in simbolos:
            _fila_simbolo(sim)
    else:
        st.info("No hay símbolos registrados todavía.")

    seccion("Añadir nuevo símbolo")
    _form_nuevo_simbolo()
