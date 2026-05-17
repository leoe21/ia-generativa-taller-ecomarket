import streamlit as st

from src.streamlit_ui import (
    inject_base_styles,
    init_session_state,
    render_chat_page,
    render_demo_guide_tab,
    render_demo_tech_panel,
    render_sidebar_demo,
)

st.set_page_config(
    page_title="EcoMarket · Sustentacion academica",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_base_styles()
init_session_state("demo")

with st.sidebar:
    provider, top_k = render_sidebar_demo()

st.title("EcoMarket")
st.caption("Asistente virtual de atencion al cliente — vista con diagnostico del agente")

tab_home, tab_guide, tab_tech = st.tabs(["Inicio", "Como usar", "Panel tecnico"])

with tab_home:
    render_chat_page(
        "demo",
        provider=provider,
        top_k=top_k,
        show_technical=True,
        welcome=(
            "Hola, soy el asistente de **EcoMarket**. "
            "Escribe tu mensaje abajo o elige un ejemplo en la barra lateral."
        ),
        input_placeholder="Mensaje para EcoMarket...",
        header_caption="El historial se desplaza hacia arriba. Escribe en la barra inferior.",
    )

with tab_guide:
    render_demo_guide_tab()

with tab_tech:
    render_demo_tech_panel(provider)

st.divider()
st.caption(
    "EcoMarket - prototipo academico. Casos sensibles (fraude, reclamos legales) deben escalarse a un agente humano."
)
