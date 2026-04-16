import json
import time

import streamlit as st
from dotenv import load_dotenv

from src.llm_client import generate_response
from src.open_source_client import generate_response_ollama
from src.rag_engine import (
    build_order_context,
    classify_return,
    find_order,
    load_orders,
    load_policies,
    load_order_prompt,
    load_returns_prompt,
)


load_dotenv()
REQUEST_COOLDOWN_SECONDS = 4


def _is_quota_error(error: Exception) -> bool:
    message = str(error).lower()
    return "429" in message or "quota" in message or "resource_exhausted" in message


def _fallback_order_answer(order: dict | None, tracking_number: str) -> str:
    if order is None:
        return (
            f"No encontre el pedido {tracking_number}. "
            "Por favor verifica el numero e intentalo de nuevo."
        )

    base = (
        f"El pedido {order['id_pedido']} se encuentra en estado: {order['estado']}. "
        f"Fecha estimada de entrega: {order['fecha_entrega_estimada']}. "
        f"Puedes revisar el seguimiento aqui: {order['tracking_url']}."
    )
    if order.get("retrasado"):
        return (
            "Lamentamos el retraso en tu envio. "
            + base
            + " Como compensacion, te ofrecemos un cupon del 5% de descuento en tu proxima compra."
        )
    return base


def _fallback_return_answer(result: dict, category: str, days_since_purchase: int) -> str:
    if result["elegible"]:
        instructions = " ".join([f"{idx + 1}) {step}" for idx, step in enumerate(result["instrucciones"])])
        return (
            f"Tu solicitud para la categoria {category} con {days_since_purchase} dias desde la compra es elegible. "
            f"{result['motivo']} Sigue estos pasos: {instructions}"
        )
    return (
        f"Tu solicitud para la categoria {category} con {days_since_purchase} dias desde la compra no es elegible. "
        f"{result['motivo']} Si necesitas apoyo adicional, podemos escalar tu caso a un agente humano."
    )


st.set_page_config(page_title="EcoMarket AI Support", page_icon=":seedling:", layout="wide")
st.title("EcoMarket - Soporte Inteligente con IA Generativa")
st.caption("Demo academica para optimizacion de atencion al cliente en e-commerce (RAG + Open-Source/Gemini)")

provider = st.sidebar.selectbox(
    "Motor de generacion",
    options=["Open-source local (Ollama)", "Gemini API"],
    index=0,
)
st.sidebar.caption("Sugerido para el taller: Open-source local (Ollama).")

if "last_request_ts" not in st.session_state:
    st.session_state.last_request_ts = 0.0


def _cooldown_ready() -> bool:
    elapsed = time.time() - st.session_state.last_request_ts
    if elapsed < REQUEST_COOLDOWN_SECONDS:
        wait = int(REQUEST_COOLDOWN_SECONDS - elapsed) + 1
        st.warning(f"Espera {wait}s antes de enviar otra solicitud.")
        return False
    st.session_state.last_request_ts = time.time()
    return True

tab_order, tab_returns, tab_data = st.tabs(
    ["Estado de pedido", "Gestion de devoluciones", "Contexto y evidencias"]
)

with tab_order:
    st.subheader("Consulta de estado de pedido")
    tracking_number = st.text_input("Numero de pedido", placeholder="Ejemplo: 12345")
    col_a, col_b = st.columns([1, 4])
    with col_a:
        run_order = st.button("Consultar estado")

    if run_order:
        if not _cooldown_ready():
            st.stop()
        if not tracking_number.strip():
            st.warning("Ingresa un numero de pedido para continuar.")
        else:
            order = find_order(tracking_number)
            order_context = build_order_context(order)
            prompt_template = load_order_prompt()
            final_prompt = prompt_template.format(
                order_context=order_context,
                tracking_number=tracking_number,
            )

            with st.spinner(f"Generando respuesta con {provider}..."):
                try:
                    if provider == "Open-source local (Ollama)":
                        answer = generate_response_ollama(final_prompt, temperature=0.2)
                    else:
                        answer = generate_response(final_prompt, temperature=0.2)
                    st.success("Respuesta generada")
                    st.caption(f"Fuente: {provider}")
                    st.write(answer)
                except Exception as error:
                    if provider == "Gemini API" and _is_quota_error(error):
                        st.warning(
                            "La API de Gemini indicó límite de uso (cuota 429). "
                            "Mientras tanto se muestra una respuesta de respaldo generada solo con los datos locales (sin LLM)."
                        )
                        st.caption(
                            "Opciones: usa **Open-source local (Ollama)** en la barra lateral, "
                            "espera a que se renueve el cupo del free tier o revisa cuotas en Google AI Studio."
                        )
                        st.write(_fallback_order_answer(order, tracking_number))
                    else:
                        st.error(f"No fue posible generar respuesta: {error}")

            with st.expander("Ver contexto recuperado (RAG)"):
                st.code(order_context)
            with st.expander("Ver prompt final"):
                st.code(final_prompt)

with tab_returns:
    st.subheader("Clasificacion y respuesta para devoluciones")
    category = st.selectbox(
        "Categoria del producto",
        options=["perecederos", "higiene", "ropa", "accesorios"],
    )
    days_since_purchase = st.number_input(
        "Dias desde la compra",
        min_value=0,
        max_value=365,
        value=10,
        step=1,
    )

    run_return = st.button("Evaluar devolucion")
    if run_return:
        if not _cooldown_ready():
            st.stop()
        result = classify_return(category, int(days_since_purchase))
        policy_context = json.dumps(load_policies(), ensure_ascii=False, indent=2)
        prompt_template = load_returns_prompt()
        final_prompt = prompt_template.format(
            policy_context=policy_context,
            category=category,
            days_since_purchase=days_since_purchase,
        )

        with st.spinner(f"Generando respuesta con {provider}..."):
            try:
                if provider == "Open-source local (Ollama)":
                    answer = generate_response_ollama(final_prompt, temperature=0.2)
                else:
                    answer = generate_response(final_prompt, temperature=0.2)
                st.success("Respuesta generada")
                st.caption(f"Fuente: {provider}")
                st.write(answer)
            except Exception as error:
                if provider == "Gemini API" and _is_quota_error(error):
                    st.warning(
                        "La API de Gemini indicó límite de uso (cuota 429). "
                        "Mientras tanto se muestra una respuesta de respaldo con las políticas locales (sin LLM)."
                    )
                    st.caption(
                        "Opciones: **Ollama** en la barra lateral, esperar o revisar cuotas en Google AI Studio."
                    )
                    st.write(_fallback_return_answer(result, category, int(days_since_purchase)))
                else:
                    st.error(f"No fue posible generar respuesta: {error}")

        st.info(f"Resultado de clasificacion previa: elegible={result['elegible']}")
        st.write(f"Motivo: {result['motivo']}")
        if result["instrucciones"]:
            st.write("Instrucciones:")
            for step in result["instrucciones"]:
                st.write(f"- {step}")

        with st.expander("Ver contexto recuperado (RAG)"):
            st.code(policy_context)
        with st.expander("Ver prompt final"):
            st.code(final_prompt)

with tab_data:
    st.subheader("Base de pedidos de prueba (10 registros)")
    st.json(load_orders())
    st.subheader("Politicas de devolucion")
    st.json(load_policies())

st.divider()
st.caption(
    "Nota: La respuesta automatiza consultas repetitivas. Los casos sensibles o complejos deben escalarse a soporte humano."
)
