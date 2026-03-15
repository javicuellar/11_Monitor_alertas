"""
admin_app.py
────────────
Aplicación Streamlit para administrar (CRUD) todas las tablas
de configuración del Monitor de Acciones.

Tablas gestionadas:
  - configuracion_planificador
  - configuracion_email
  - configuracion_telegram
  - simbolos
  - historial_alertas  (solo lectura + limpieza)
"""

import re
import sqlite3
import os
import streamlit as st
import pandas as pd

# ── Ruta de BD ────────────────────────────────────────────────────────────────
RUTA_BD = os.environ.get(
    "RUTA_BD",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "monitor.db"),
)

# ── Helpers BD ────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(RUTA_BD)
    c.row_factory = sqlite3.Row
    return c

def ejecutar(sql: str, params: tuple = ()) -> None:
    with _conn() as c:
        c.execute(sql, params)

def consultar(sql: str, params: tuple = ()) -> list[dict]:
    with _conn() as c:
        rows = c.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


# ── Estilos ───────────────────────────────────────────────────────────────────

def inyectar_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;600&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'IBM Plex Sans', sans-serif !important;
    }

    /* ── Fondo general ── */
    .stApp {
        background-color: #f4f6f9 !important;
    }

    /* ── Contenido principal ── */
    .main .block-container {
        padding: 2rem 2.5rem 3rem 2.5rem !important;
        max-width: 1100px;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: #ffffff !important;
        border-right: 1px solid #e0e6ed !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.5rem;
    }

    /* ── Títulos ── */
    h1 {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 1.45rem !important;
        font-weight: 600 !important;
        color: #1a2332 !important;
        border-bottom: 3px solid #2563eb;
        padding-bottom: 10px;
        margin-bottom: 1.5rem !important;
        letter-spacing: -0.01em;
    }
    h2 {
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-size: 0.78rem !important;
        font-weight: 600 !important;
        color: #6b7a8d !important;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-top: 2rem !important;
        margin-bottom: 0.75rem !important;
    }
    h3 {
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-size: 1rem !important;
        color: #1a2332 !important;
    }

    /* ── Tarjetas de info ── */
    .card {
        background: #ffffff;
        border: 1px solid #e0e6ed;
        border-radius: 8px;
        padding: 18px 20px;
        margin-bottom: 16px;
    }
    .card-azul   { border-left: 4px solid #2563eb; }
    .card-verde  { border-left: 4px solid #16a34a; }
    .card-naranja{ border-left: 4px solid #ea580c; }
    .card-rojo   { border-left: 4px solid #dc2626; }

    /* ── Badges ── */
    .badge {
        display: inline-block;
        border-radius: 20px;
        padding: 2px 10px;
        font-size: 0.7rem;
        font-weight: 600;
        font-family: 'IBM Plex Mono', monospace;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .badge-verde  { background:#dcfce7; color:#15803d; border:1px solid #bbf7d0; }
    .badge-rojo   { background:#fee2e2; color:#b91c1c; border:1px solid #fecaca; }
    .badge-azul   { background:#dbeafe; color:#1d4ed8; border:1px solid #bfdbfe; }

    /* ── Inputs ── */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input {
        background: #ffffff !important;
        border: 1.5px solid #d1d9e0 !important;
        border-radius: 6px !important;
        color: #1a2332 !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-size: 0.9rem !important;
        padding: 8px 12px !important;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: #2563eb !important;
        box-shadow: 0 0 0 3px rgba(37,99,235,0.1) !important;
        outline: none !important;
    }
    .stTextInput label, .stNumberInput label,
    .stSelectbox label, .stCheckbox label {
        color: #4b5563 !important;
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        margin-bottom: 4px !important;
    }

    /* ── Selectbox ── */
    .stSelectbox > div > div {
        background: #ffffff !important;
        border: 1.5px solid #d1d9e0 !important;
        border-radius: 6px !important;
        color: #1a2332 !important;
    }

    /* ── Checkbox ── */
    .stCheckbox span {
        color: #374151 !important;
        font-size: 0.9rem !important;
    }

    /* ── Botones ── */
    .stButton > button {
        background: #ffffff;
        border: 1.5px solid #2563eb;
        color: #2563eb;
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 0.85rem;
        font-weight: 500;
        padding: 7px 18px;
        border-radius: 6px;
        transition: all 0.15s ease;
        letter-spacing: 0.01em;
    }
    .stButton > button:hover {
        background: #2563eb;
        color: #ffffff;
        border-color: #2563eb;
    }
    .stButton > button:active {
        background: #1d4ed8;
        transform: translateY(1px);
    }

    /* Botón primario */
    .btn-primario .stButton > button {
        background: #2563eb;
        color: #ffffff;
        border: none;
        font-weight: 600;
        width: 100%;
        padding: 9px 18px;
    }
    .btn-primario .stButton > button:hover {
        background: #1d4ed8;
        box-shadow: 0 4px 12px rgba(37,99,235,0.25);
    }

    /* Botón peligro */
    .btn-peligro .stButton > button {
        border-color: #dc2626;
        color: #dc2626;
    }
    .btn-peligro .stButton > button:hover {
        background: #dc2626;
        color: white;
    }

    /* ── Métricas ── */
    [data-testid="metric-container"] {
        background: #ffffff;
        border: 1px solid #e0e6ed;
        border-radius: 8px;
        padding: 18px 20px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    [data-testid="metric-container"] label {
        color: #6b7a8d !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    [data-testid="stMetricValue"] {
        color: #1a2332 !important;
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 1.7rem !important;
        font-weight: 600 !important;
    }

    /* ── Tablas / dataframe ── */
    [data-testid="stDataFrame"] {
        border: 1px solid #e0e6ed !important;
        border-radius: 8px !important;
        overflow: hidden !important;
        background: #ffffff !important;
    }
    [data-testid="stDataFrame"] table {
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-size: 0.85rem !important;
    }

    /* ── Expanders ── */
    [data-testid="stExpander"] {
        background: #ffffff !important;
        border: 1px solid #e0e6ed !important;
        border-radius: 8px !important;
        margin-bottom: 8px !important;
    }
    [data-testid="stExpander"] summary {
        color: #1a2332 !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        padding: 12px 16px !important;
    }
    [data-testid="stExpander"] summary:hover {
        background: #f8fafc !important;
    }

    /* ── Mensajes de estado ── */
    [data-testid="stNotification"],
    div[class*="stAlert"] {
        border-radius: 6px !important;
        font-size: 0.88rem !important;
    }

    /* ── Divisores ── */
    hr {
        border: none !important;
        border-top: 1px solid #e0e6ed !important;
        margin: 1.5rem 0 !important;
    }

    /* ── Sidebar logo ── */
    .logo-bloque {
        padding: 0 0 1.5rem 0;
        border-bottom: 1px solid #e0e6ed;
        margin-bottom: 1.2rem;
    }
    .logo-titulo {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 1.05rem;
        font-weight: 600;
        color: #1a2332;
        letter-spacing: -0.02em;
    }
    .logo-titulo span { color: #2563eb; }
    .logo-sub {
        font-size: 0.68rem;
        color: #9ca3af;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-top: 3px;
    }
    .bd-info {
        font-size: 0.72rem;
        color: #9ca3af;
        font-family: 'IBM Plex Mono', monospace;
        padding-top: 1rem;
        border-top: 1px solid #e0e6ed;
        margin-top: 1rem;
    }
    .bd-info span { color: #2563eb; }

    /* ── Nav radio ── */
    [data-testid="stSidebar"] .stRadio > div {
        gap: 2px !important;
    }
    [data-testid="stSidebar"] .stRadio label {
        border-radius: 6px !important;
        padding: 8px 12px !important;
        color: #4b5563 !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        transition: background 0.1s;
        cursor: pointer;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        background: #f1f5fe !important;
        color: #2563eb !important;
    }
    </style>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# COMPONENTES REUTILIZABLES
# ══════════════════════════════════════════════════════════════════════════════

def seccion(titulo: str):
    st.markdown(f"## {titulo}")

def card(contenido_html: str, tipo: str = "azul"):
    st.markdown(
        f'<div class="card card-{tipo}">{contenido_html}</div>',
        unsafe_allow_html=True,
    )

def badge(texto: str, tipo: str = "azul") -> str:
    return f'<span class="badge badge-{tipo}">{texto}</span>'


# ══════════════════════════════════════════════════════════════════════════════
# PÁGINAS
# ══════════════════════════════════════════════════════════════════════════════

def pagina_dashboard():
    st.title("📊 Panel de Control")

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

    # ── Métricas ──────────────────────────────────────────────────────────────
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
        <div style="font-size:1rem;font-weight:600;color:#1a2332;">
            {'✅ Activo' if email_ok else '❌ Inactivo'}
        </div>
        {f'<div style="font-size:0.8rem;color:#6b7a8d;margin-top:4px;">{cfg_email[0]["servidor_smtp"]}:{cfg_email[0]["puerto_smtp"]}</div>' if cfg_email else ''}
        </div>""",
        unsafe_allow_html=True,
    )

    cfg_tg = consultar("SELECT * FROM configuracion_telegram LIMIT 1")
    col_t.markdown(
        f"""<div class="card card-{'verde' if tg_ok else 'rojo'}">
        <div style="font-size:0.75rem;color:#6b7a8d;text-transform:uppercase;letter-spacing:0.08em;margin-bottom:6px;">Telegram Bot</div>
        <div style="font-size:1rem;font-weight:600;color:#1a2332;">
            {'✅ Activo' if tg_ok else '❌ Inactivo'}
        </div>
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
               ROUND(cierre_anterior,2)   AS "Cierre ant.",
               ROUND(precio_actual,2)     AS "Precio act.",
               ROUND(cambio_porcentaje,2) AS "Cambio %",
               direccion                  AS "Dir.",
               CASE WHEN notificado_email=1    THEN '✅' ELSE '❌' END AS "Email",
               CASE WHEN notificado_telegram=1 THEN '✅' ELSE '❌' END AS "TG",
               creado_en
        FROM historial_alertas ORDER BY creado_en DESC LIMIT 20
    """)
    if alertas:
        df = pd.DataFrame(alertas)
        df.columns = ["Ticker","Fecha","Cierre ant.","Precio act.","Cambio %","Dir.","Email","TG","Creado"]
        st.dataframe(df, hide_index=True)
    else:
        st.info("Todavía no hay alertas registradas.")

    # ── Símbolos activos ──────────────────────────────────────────────────────
    seccion("Símbolos monitorizados")
    sims = consultar("SELECT ticker, nombre, umbral, activo FROM simbolos ORDER BY ticker")
    if sims:
        df2 = pd.DataFrame(sims)
        df2["activo"] = df2["activo"].apply(lambda x: "🟢 Activo" if x else "🔴 Inactivo")
        df2.columns   = ["Ticker", "Nombre", "Umbral %", "Estado"]
        st.dataframe(df2, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────

def pagina_planificador():
    st.title("⏱ Planificador")
    filas = consultar("SELECT * FROM configuracion_planificador LIMIT 1")

    if not filas:
        st.error("No hay configuración del planificador en la base de datos.")
        return

    cfg = filas[0]

    seccion("Parámetros de ejecución")
    with st.form("form_planificador"):
        c1, c2 = st.columns(2)
        intervalo   = c1.number_input("Intervalo entre comprobaciones (minutos)",
                                      min_value=1, max_value=1440, value=int(cfg["intervalo_minutos"]))
        solo_lab    = c2.checkbox("Solo días laborables (Lunes a Viernes)",
                                  value=bool(cfg["solo_laborables"]))
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

    seccion("Resumen de configuración activa")
    dias = "Lunes a Viernes" if cfg["solo_laborables"] else "Todos los días"
    card(
        f"""
        <div style="display:flex;gap:32px;flex-wrap:wrap;align-items:center;">
            <div><span style="font-size:0.72rem;color:#6b7a8d;text-transform:uppercase;letter-spacing:0.08em;">Frecuencia</span>
                 <div style="font-size:1.1rem;font-weight:600;color:#1a2332;margin-top:2px;">🔁 Cada {cfg['intervalo_minutos']} min</div></div>
            <div><span style="font-size:0.72rem;color:#6b7a8d;text-transform:uppercase;letter-spacing:0.08em;">Ventana horaria</span>
                 <div style="font-size:1.1rem;font-weight:600;color:#1a2332;margin-top:2px;">🕐 {cfg['hora_inicio']} — {cfg['hora_fin']}</div></div>
            <div><span style="font-size:0.72rem;color:#6b7a8d;text-transform:uppercase;letter-spacing:0.08em;">Días activos</span>
                 <div style="font-size:1.1rem;font-weight:600;color:#1a2332;margin-top:2px;">📅 {dias}</div></div>
        </div>
        """,
        tipo="azul",
    )


# ─────────────────────────────────────────────────────────────────────────────

def _form_email(cfg: dict | None):
    es_nuevo = cfg is None
    defaults = cfg or {
        "servidor_smtp": "smtp.gmail.com", "puerto_smtp": 587,
        "usuario": "", "contrasena": "", "direccion_origen": "",
        "direccion_destino": "", "activo": 0,
    }

    with st.form("form_email"):
        c1, c2    = st.columns([3, 1])
        servidor  = c1.text_input("Servidor SMTP",          value=defaults["servidor_smtp"])
        puerto    = c2.number_input("Puerto", min_value=1, max_value=65535,
                                    value=int(defaults["puerto_smtp"]))
        usuario   = st.text_input("Usuario (dirección de email)", value=defaults["usuario"])
        contrasena = st.text_input("Contraseña / App Password",
                                   value=defaults["contrasena"], type="password")
        c3, c4    = st.columns(2)
        dir_orig  = c3.text_input("Dirección de envío (origen)",  value=defaults["direccion_origen"])
        dir_dest  = c4.text_input("Dirección de recepción (destino)", value=defaults["direccion_destino"])
        activo    = st.checkbox("Activar notificaciones por email", value=bool(defaults["activo"]))

        st.markdown('<div class="btn-primario">', unsafe_allow_html=True)
        enviado = st.form_submit_button("➕ Crear configuración" if es_nuevo else "💾 Guardar cambios")
        st.markdown('</div>', unsafe_allow_html=True)

        if enviado:
            if es_nuevo:
                ejecutar(
                    "INSERT INTO configuracion_email "
                    "(servidor_smtp, puerto_smtp, usuario, contrasena, "
                    " direccion_origen, direccion_destino, activo) VALUES (?,?,?,?,?,?,?)",
                    (servidor, puerto, usuario, contrasena, dir_orig, dir_dest, int(activo)),
                )
                st.success("✅ Configuración de email creada.")
            else:
                ejecutar(
                    "UPDATE configuracion_email SET servidor_smtp=?, puerto_smtp=?, "
                    "usuario=?, contrasena=?, direccion_origen=?, direccion_destino=?, "
                    "activo=? WHERE id=?",
                    (servidor, puerto, usuario, contrasena, dir_orig, dir_dest,
                     int(activo), cfg["id"]),
                )
                st.success("✅ Configuración de email guardada.")
            st.rerun()


def pagina_email():
    st.title("📧 Email")
    filas = consultar("SELECT * FROM configuracion_email")

    seccion("Configuración SMTP")
    if not filas:
        st.warning("No hay configuración de email todavía. Rellena el formulario para crearla.")
    _form_email(filas[0] if filas else None)

    seccion("Ayuda — Gmail / App Password")
    card(
        """
        <p style="margin:0 0 10px 0;font-weight:600;color:#92400e;">⚠️ Gmail requiere una <em>App Password</em>, no tu contraseña habitual</p>
        <p style="margin:0;color:#4b5563;font-size:0.88rem;line-height:1.6;">
            Ve a <strong>Cuenta de Google → Seguridad → Verificación en 2 pasos → Contraseñas de aplicaciones</strong>.<br>
            Genera una contraseña para «Correo» y úsala en el campo de arriba.
        </p>
        """,
        tipo="naranja",
    )


# ─────────────────────────────────────────────────────────────────────────────

def _form_telegram(cfg: dict | None):
    es_nuevo = cfg is None
    defaults = cfg or {"token_bot": "", "id_chat": "", "activo": 0}

    with st.form("form_telegram"):
        token   = st.text_input("Token del Bot",          value=defaults["token_bot"], type="password")
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


def pagina_telegram():
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
            <li>Abre Telegram y escribe a <strong>@BotFather</strong>. Envía <code>/newbot</code> y sigue los pasos → recibirás el token.</li>
            <li>Para tu chat personal: escribe a <strong>@userinfobot</strong> y te dirá tu ID.</li>
            <li>Para un grupo: añade el bot al grupo y llama a <code>https://api.telegram.org/bot&lt;TOKEN&gt;/getUpdates</code>.</li>
        </ol>
        """,
        tipo="azul",
    )


# ─────────────────────────────────────────────────────────────────────────────

def pagina_simbolos():
    st.title("📈 Símbolos")

    seccion("Símbolos registrados")
    simbolos = consultar("SELECT id, ticker, nombre, umbral, activo FROM simbolos ORDER BY ticker")

    if simbolos:
        for sim in simbolos:
            tipo_badge = "verde" if sim["activo"] else "rojo"
            etiqueta   = "ACTIVO" if sim["activo"] else "INACTIVO"
            label_exp  = f"{sim['ticker']}  —  {sim['nombre'] or '—'}"
            with st.expander(label_exp, expanded=False):
                st.markdown(
                    f'<div style="margin-bottom:12px;">{badge(etiqueta, tipo_badge)}</div>',
                    unsafe_allow_html=True,
                )
                with st.form(f"form_sim_{sim['id']}"):
                    c1, c2   = st.columns([2, 1])
                    ticker_e = c1.text_input("Ticker",  value=sim["ticker"],     key=f"tk_{sim['id']}")
                    umbral_e = c2.number_input("Umbral de alerta (%)",
                                               value=float(sim["umbral"]),
                                               min_value=0.1, max_value=100.0, step=0.1,
                                               key=f"ub_{sim['id']}")
                    nombre_e = st.text_input("Nombre descriptivo", value=sim["nombre"] or "",
                                             key=f"nm_{sim['id']}")
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
                        ejecutar(
                            "UPDATE simbolos SET ticker=?, nombre=?, umbral=?, activo=? WHERE id=?",
                            (ticker_e.strip().upper(), nombre_e.strip(), umbral_e,
                             int(activo_e), sim["id"]),
                        )
                        st.success(f"✅ {ticker_e.upper()} actualizado.")
                        st.rerun()
                    if eliminar:
                        ejecutar("DELETE FROM simbolos WHERE id=?", (sim["id"],))
                        st.success(f"🗑 {sim['ticker']} eliminado.")
                        st.rerun()
    else:
        st.info("No hay símbolos registrados todavía.")

    seccion("Añadir nuevo símbolo")
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


# ─────────────────────────────────────────────────────────────────────────────

def pagina_historial():
    st.title("📜 Historial de Alertas")

    seccion("Filtros")
    c1, c2, c3 = st.columns(3)
    tickers_bd = [r["ticker"] for r in consultar(
        "SELECT DISTINCT ticker FROM historial_alertas ORDER BY ticker"
    )]
    filtro_ticker = c1.selectbox("Ticker", ["Todos"] + tickers_bd)
    filtro_dir    = c2.selectbox("Dirección", ["Todas", "▲ SUBE", "▼ BAJA"])
    filtro_n      = c3.number_input("Últimos N registros", value=50, min_value=1, max_value=1000)

    where, params = [], []
    if filtro_ticker != "Todos":
        where.append("ticker=?");  params.append(filtro_ticker)
    if filtro_dir != "Todas":
        where.append("direccion=?"); params.append(filtro_dir)

    sql = "SELECT * FROM historial_alertas"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY creado_en DESC LIMIT {int(filtro_n)}"

    alertas = consultar(sql, tuple(params))

    if not alertas:
        st.info("No hay alertas con los filtros seleccionados.")
    else:
        seccion(f"{len(alertas)} registros")
        df = pd.DataFrame(alertas)
        df["notificado_email"]    = df["notificado_email"].map({1: "✅", 0: "❌"})
        df["notificado_telegram"] = df["notificado_telegram"].map({1: "✅", 0: "❌"})
        df["cambio_porcentaje"]   = df["cambio_porcentaje"].apply(lambda x: f"{x:+.2f}%")
        df = df.drop(columns=["id"])
        df.columns = ["Ticker","Fecha","Cierre ant.","Precio act.","Cambio","Dir.","Email","TG","Creado"]
        st.dataframe(df, hide_index=True)

    st.markdown("---")
    seccion("⚠️ Zona peligrosa")
    col1, _ = st.columns([1, 3])
    with col1:
        st.markdown('<div class="btn-peligro">', unsafe_allow_html=True)
        if st.button("🗑 Limpiar historial completo"):
            st.session_state["confirmar_limpieza"] = True
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.get("confirmar_limpieza"):
        st.warning("¿Estás seguro? Esta acción eliminará **todos** los registros del historial y no se puede deshacer.")
        cc1, cc2, _ = st.columns([1, 1, 2])
        if cc1.button("✅ Sí, borrar todo"):
            ejecutar("DELETE FROM historial_alertas")
            st.session_state["confirmar_limpieza"] = False
            st.success("Historial eliminado correctamente.")
            st.rerun()
        if cc2.button("❌ Cancelar"):
            st.session_state["confirmar_limpieza"] = False
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    st.set_page_config(
        page_title="Monitor de Acciones — Admin",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inyectar_css()

    with st.sidebar:
        st.markdown("""
        <div class="logo-bloque">
            <div class="logo-titulo">📈 Monitor<span>Admin</span></div>
            <div class="logo-sub">Panel de administración</div>
        </div>
        """, unsafe_allow_html=True)

        pagina = st.radio(
            "nav",
            options=["📊 Panel de Control", "⏱ Planificador", "📧 Email",
                     "✈️ Telegram", "📈 Símbolos", "📜 Historial"],
            label_visibility="collapsed",
        )

        st.markdown(
            f'<div class="bd-info">Base de datos<br><span>{os.path.basename(RUTA_BD)}</span></div>',
            unsafe_allow_html=True,
        )

    rutas = {
        "📊 Panel de Control": pagina_dashboard,
        "⏱ Planificador":      pagina_planificador,
        "📧 Email":             pagina_email,
        "✈️ Telegram":          pagina_telegram,
        "📈 Símbolos":          pagina_simbolos,
        "📜 Historial":         pagina_historial,
    }
    rutas[pagina]()




if __name__ == "__main__":
    main()
