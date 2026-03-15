"""
admin_app.py
────────────
Punto de entrada de la aplicación Streamlit de administración.

Responsabilidades de este archivo:
  - Configurar la página (set_page_config)
  - Inyectar los estilos globales
  - Renderizar el sidebar y obtener la página activa
  - Delegar el render a cada módulo de página

Las páginas y la lógica están en el paquete `admin/`:
  admin/db.py                 → acceso a la base de datos
  admin/ui.py                 → CSS y componentes compartidos
  admin/pagina_dashboard.py   → Panel de Control
  admin/pagina_planificador.py→ Planificador
  admin/pagina_email.py       → Email
  admin/pagina_telegram.py    → Telegram
  admin/pagina_simbolos.py    → Símbolos
  admin/pagina_historial.py   → Historial de alertas
"""

import streamlit as st

from admin import (
    pagina_dashboard,
    pagina_email,
    pagina_historial,
    pagina_planificador,
    pagina_simbolos,
    pagina_telegram,
)
from admin.ui import inyectar_css, renderizar_sidebar



# Mapa de opción de navegación → módulo de página
_RUTAS = {
    "📊 Panel de Control": pagina_dashboard,
    "⏱ Planificador":      pagina_planificador,
    "📧 Email":             pagina_email,
    "✈️ Telegram":          pagina_telegram,
    "📈 Símbolos":          pagina_simbolos,
    "📜 Historial":         pagina_historial,
}



def main() -> None:
    st.set_page_config(
        page_title="Monitor de Acciones — Admin",
        page_icon="📈",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inyectar_css()
    pagina = renderizar_sidebar()
    _RUTAS[pagina].render()




if __name__ == "__main__":
    main()
