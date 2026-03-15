"""
admin/pagina_email.py
─────────────────────
Pantalla: Configuración de Email.
Gestiona los parámetros SMTP para el envío de notificaciones.
"""

import streamlit as st

from .db import consultar, ejecutar
from .ui import card, seccion


def _form_email(cfg: dict | None) -> None:
    """Renderiza el formulario de creación o edición de email."""
    es_nuevo = cfg is None
    defaults = cfg or {
        "servidor_smtp": "smtp.gmail.com", "puerto_smtp": 587,
        "usuario": "", "password": "", "direccion_origen": "",
        "direccion_destino": "", "activo": 0,
    }

    with st.form("form_email"):
        c1, c2 = st.columns([3, 1])
        servidor   = c1.text_input("Servidor SMTP",               value=defaults["servidor_smtp"])
        puerto     = c2.number_input("Puerto", min_value=1, max_value=65535,
                                     value=int(defaults["puerto_smtp"]))
        usuario    = st.text_input("Usuario (dirección de email)", value=defaults["usuario"])
        password = st.text_input("Contraseña / App Password",
                                 value=defaults["password"], type="password")
        c3, c4 = st.columns(2)
        dir_orig = c3.text_input("Dirección de envío (origen)",       value=defaults["direccion_origen"])
        dir_dest = c4.text_input("Dirección de recepción (destino)",  value=defaults["direccion_destino"])
        activo   = st.checkbox("Activar notificaciones por email",    value=bool(defaults["activo"]))

        st.markdown('<div class="btn-primario">', unsafe_allow_html=True)
        enviado = st.form_submit_button("➕ Crear configuración" if es_nuevo else "💾 Guardar cambios")
        st.markdown('</div>', unsafe_allow_html=True)

        if enviado:
            if es_nuevo:
                ejecutar(
                    "INSERT INTO configuracion_email "
                    "(servidor_smtp, puerto_smtp, usuario, password, "
                    " direccion_origen, direccion_destino, activo) VALUES (?,?,?,?,?,?,?)",
                    (servidor, puerto, usuario, password, dir_orig, dir_dest, int(activo)),
                )
                st.success("✅ Configuración de email creada.")
            else:
                ejecutar(
                    "UPDATE configuracion_email SET servidor_smtp=?, puerto_smtp=?, "
                    "usuario=?, password=?, direccion_origen=?, direccion_destino=?, "
                    "activo=? WHERE id=?",
                    (servidor, puerto, usuario, password, dir_orig, dir_dest,
                     int(activo), cfg["id"]),
                )
                st.success("✅ Configuración de email guardada.")
            st.rerun()


def render() -> None:
    st.title("📧 Email")

    filas = consultar("SELECT * FROM configuracion_email")

    seccion("Configuración SMTP")
    if not filas:
        st.warning("No hay configuración de email todavía. Rellena el formulario para crearla.")
    _form_email(filas[0] if filas else None)

    seccion("Ayuda — Gmail / App Password")
    card(
        """
        <p style="margin:0 0 10px 0;font-weight:600;color:#92400e;">
            ⚠️ Gmail requiere una <em>App Password</em>, no tu contraseña habitual
        </p>
        <p style="margin:0;color:#4b5563;font-size:0.88rem;line-height:1.6;">
            Ve a <strong>Cuenta de Google → Seguridad → Verificación en 2 pasos
            → Contraseñas de aplicaciones</strong>.<br>
            Genera una contraseña para «Correo» y úsala en el campo de arriba.
        </p>
        """,
        tipo="naranja",
    )
