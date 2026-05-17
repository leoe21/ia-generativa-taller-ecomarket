import streamlit as st

from src.streamlit_ui import (
    DEFAULT_PROVIDER,
    inject_base_styles,
    init_session_state,
    render_chat_page,
    render_sidebar_client,
)

st.set_page_config(
    page_title="EcoMarket · Atencion al cliente",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

inject_base_styles()
init_session_state("client")

with st.sidebar:
    top_k = render_sidebar_client()

st.title("EcoMarket")
st.caption("Estamos aqui para ayudarte con pedidos, devoluciones y consultas de la tienda")

render_chat_page(
    "client",
    provider=DEFAULT_PROVIDER,
    top_k=top_k,
    show_technical=False,
    welcome=(
        "Hola, soy tu asistente de **EcoMarket**. "
        "Puedo ayudarte con el estado de tu pedido, devoluciones, pagos y envios. "
        "Cuentame en que te puedo apoyar."
    ),
    input_placeholder="Escribe tu mensaje...",
    header_caption=None,
)

st.divider()
st.caption(
    "Al continuar aceptas que este chat es atendido por un asistente automatizado. "
    "Para reclamos sensibles o legales, escribenos a **soporte@ecomarket.co**."
)
