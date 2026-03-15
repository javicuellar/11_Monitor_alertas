"""
admin/pagina_telegram.py
────────────────────────
Pantalla: Configuración de Telegram.
Gestiona el token del bot y el chat ID para notificaciones.
"""

import streamlit as st

from .db import consultar, ejecutar
from .ui import card, seccion


def _form_telegram(cfg: dict | None) -> None:
    """Renderiza el formulario de creación o edición de Telegram."""
    es_nuevo = cfg is None
    defaults = cfg or {"token_bot": "", "id_chat": "", "activo": 0}

    with st.form("form_telegram"):
        token   = st.text_input("Token del Bot",           value=defaults["token_bot"], type="password")
        id_chat = st.text_input("ID del Chat o del Grupo", value=defaults["id_chat"])
        activo  = st.checkbox("Activar notificaciones por Telegram", value=bool(defaults["activo"]))

        st.markdown('<div class="btn-primario">', unsafe_allow_html=True)
        enviado = st.form_submit_button("➕ Crear configuración" if es_nuevo else "💾 Guardar cambios")
        st.markdown('</div>', unsafe_allow_html=True)

        if enviado:
            if es_nuevo:
                ejecutar(
                    "INSERT INTO configuracion_telegram (token_bot, id_chat, activo) VALUES (?,?,?)",
                    (token, id_chat, int(activo)),
                )
                st.success("✅ Configuración de Telegram creada.")
            else:
                ejecutar(
                    "UPDATE configuracion_telegram SET token_bot=?, id_chat=?, activo=? WHERE id=?",
                    (token, id_chat, int(activo), cfg["id"]),
                )
                st.success("✅ Configuración de Telegram guardada.")
            st.rerun()


def render() -> None:
    st.title("✈️ Telegram")

    filas = consultar("SELECT * FROM configuracion_telegram")

    seccion("Bot API")
    if not filas:
        st.warning("No hay configuración de Telegram todavía.")
    _form_telegram(filas[0] if filas else None)

    seccion("Cómo obtener el token y el chat ID")
    card(
        """
        <ol style="margin:0;padding-left:20px;color:#374151;font-size:0.88rem;line-height:2;">
            <li>Abre Telegram y escribe a <strong>@BotFather</strong>.
                Envía <code>/newbot</code> y sigue los pasos → recibirás el token.</li>
            <li>Para tu chat personal: escribe a <strong>@userinfobot</strong> y te dirá tu ID.</li>
            <li>Para un grupo: añade el bot al grupo y llama a
                <code>https://api.telegram.org/bot&lt;TOKEN&gt;/getUpdates</code>.</li>
        </ol>
        """,
        tipo="azul",
    )
