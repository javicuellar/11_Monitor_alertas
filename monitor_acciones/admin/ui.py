"""
admin/ui.py
───────────
Componentes de UI reutilizables (CSS, helpers de maquetación) compartidos
por todas las páginas del panel de administración.
"""

import os
import streamlit as st

from .db import RUTA_BD


# ── CSS global ────────────────────────────────────────────────────────────────

def inyectar_css() -> None:
    """Inyecta la hoja de estilos global en la página Streamlit activa."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;600&display=swap');

    html, body, [class*="css"], .stApp {
        font-family: 'IBM Plex Sans', sans-serif !important;
    }

    .stApp { background-color: #f4f6f9 !important; }

    .main .block-container {
        padding: 2rem 2.5rem 3rem 2.5rem !important;
        max-width: 1100px;
    }

    [data-testid="stSidebar"] {
        background: #ffffff !important;
        border-right: 1px solid #e0e6ed !important;
    }
    [data-testid="stSidebar"] > div:first-child { padding-top: 1.5rem; }

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

    .card {
        background: #ffffff;
        border: 1px solid #e0e6ed;
        border-radius: 8px;
        padding: 18px 20px;
        margin-bottom: 16px;
    }
    .card-azul    { border-left: 4px solid #2563eb; }
    .card-verde   { border-left: 4px solid #16a34a; }
    .card-naranja { border-left: 4px solid #ea580c; }
    .card-rojo    { border-left: 4px solid #dc2626; }

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

    .stSelectbox > div > div {
        background: #ffffff !important;
        border: 1.5px solid #d1d9e0 !important;
        border-radius: 6px !important;
        color: #1a2332 !important;
    }
    .stCheckbox span { color: #374151 !important; font-size: 0.9rem !important; }

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
    }
    .stButton > button:hover { background: #2563eb; color: #ffffff; }
    .stButton > button:active { background: #1d4ed8; transform: translateY(1px); }

    .btn-primario .stButton > button {
        background: #2563eb; color: #ffffff; border: none;
        font-weight: 600; width: 100%; padding: 9px 18px;
    }
    .btn-primario .stButton > button:hover {
        background: #1d4ed8;
        box-shadow: 0 4px 12px rgba(37,99,235,0.25);
    }
    .btn-peligro .stButton > button { border-color: #dc2626; color: #dc2626; }
    .btn-peligro .stButton > button:hover { background: #dc2626; color: white; }

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
    [data-testid="stExpander"] summary:hover { background: #f8fafc !important; }

    [data-testid="stNotification"], div[class*="stAlert"] {
        border-radius: 6px !important;
        font-size: 0.88rem !important;
    }

    hr { border: none !important; border-top: 1px solid #e0e6ed !important; margin: 1.5rem 0 !important; }

    .logo-bloque { padding: 0 0 1.5rem 0; border-bottom: 1px solid #e0e6ed; margin-bottom: 1.2rem; }
    .logo-titulo { font-family: 'IBM Plex Mono', monospace; font-size: 1.05rem; font-weight: 600; color: #1a2332; letter-spacing: -0.02em; }
    .logo-titulo span { color: #2563eb; }
    .logo-sub { font-size: 0.68rem; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.1em; margin-top: 3px; }
    .bd-info { font-size: 0.72rem; color: #9ca3af; font-family: 'IBM Plex Mono', monospace; padding-top: 1rem; border-top: 1px solid #e0e6ed; margin-top: 1rem; }
    .bd-info span { color: #2563eb; }

    [data-testid="stSidebar"] .stRadio > div { gap: 2px !important; }
    [data-testid="stSidebar"] .stRadio label {
        border-radius: 6px !important; padding: 8px 12px !important;
        color: #4b5563 !important; font-size: 0.88rem !important; font-weight: 500 !important;
        transition: background 0.1s; cursor: pointer;
    }
    [data-testid="stSidebar"] .stRadio label:hover { background: #f1f5fe !important; color: #2563eb !important; }
    </style>
    """, unsafe_allow_html=True)


# ── Helpers de maquetación ────────────────────────────────────────────────────

def seccion(titulo: str) -> None:
    """Renderiza un encabezado de sección en estilo h2."""
    st.markdown(f"## {titulo}")


def card(contenido_html: str, tipo: str = "azul") -> None:
    """Renderiza una tarjeta con borde de color."""
    st.markdown(
        f'<div class="card card-{tipo}">{contenido_html}</div>',
        unsafe_allow_html=True,
    )


def badge(texto: str, tipo: str = "azul") -> str:
    """Devuelve el HTML de un badge de estado inline."""
    return f'<span class="badge badge-{tipo}">{texto}</span>'


def renderizar_sidebar() -> str:
    """
    Renderiza el sidebar con logo, navegación y pie.
    Devuelve la página seleccionada por el usuario.
    """
    with st.sidebar:
        st.markdown("""
        <div class="logo-bloque">
            <div class="logo-titulo">📈 Monitor<span>Admin</span></div>
            <div class="logo-sub">Panel de administración</div>
        </div>
        """, unsafe_allow_html=True)

        pagina = st.radio(
            "nav",
            options=[
                "📊 Panel de Control",
                "⏱ Planificador",
                "📧 Email",
                "✈️ Telegram",
                "📈 Símbolos",
                "📜 Historial",
            ],
            label_visibility="collapsed",
        )

        st.markdown(
            f'<div class="bd-info">Base de datos<br><span>{os.path.basename(RUTA_BD)}</span></div>',
            unsafe_allow_html=True,
        )

    return pagina
