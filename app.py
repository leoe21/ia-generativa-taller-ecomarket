"""
EcoMarket — punto de entrada Streamlit.

Navegacion:
  - Atencion al cliente: experiencia limpia para usuario final.
  - Sustentacion academica: router visible, panel tecnico y configuracion LLM.
"""

from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent

try:
    pages = st.navigation(
        {
            "EcoMarket": [
                st.Page(
                    ROOT / "views" / "cliente.py",
                    title="Atencion al cliente",
                    icon="💬",
                    default=True,
                ),
                st.Page(
                    ROOT / "views" / "sustentacion.py",
                    title="Sustentacion academica",
                    icon="🎓",
                ),
            ],
        }
    )
    pages.run()
except AttributeError:
    # Streamlit antiguo sin st.navigation: pagina unica con selector
    import importlib.util

    st.set_page_config(
        page_title="EcoMarket",
        page_icon="🌱",
        layout="wide",
    )
    vista = st.radio(
        "Selecciona la vista",
        options=["Atencion al cliente", "Sustentacion academica"],
        horizontal=True,
    )
    script = "cliente.py" if vista == "Atencion al cliente" else "sustentacion.py"
    path = ROOT / "views" / script
    spec = importlib.util.spec_from_file_location("ecomarket_view", path)
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        st.error("No se pudo cargar la vista seleccionada. Actualiza Streamlit: pip install -U streamlit")
