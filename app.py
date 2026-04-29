import json
import time

import streamlit as st
from dotenv import load_dotenv

from src.hf_client import generate_response_hf
from src.llm_client import generate_response
from src.open_source_client import generate_response_ollama
from src.rag_engine import (
    build_general_rag_prompt,
    build_order_context,
    classify_return,
    find_order,
    format_retrieved_context,
    get_embedding_model_name,
    get_knowledge_base_summary,
    get_rag_top_k,
    get_vector_store,
    has_sufficient_context,
    load_orders,
    load_policies,
    load_order_prompt,
    load_returns_prompt,
    retrieve_knowledge,
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
        instructions = " ".join(
            [f"{idx + 1}) {step}" for idx, step in enumerate(result["instrucciones"])]
        )
        return (
            f"Tu solicitud para la categoria {category} con {days_since_purchase} dias desde la compra es elegible. "
            f"{result['motivo']} Sigue estos pasos: {instructions}"
        )
    return (
        f"Tu solicitud para la categoria {category} con {days_since_purchase} dias desde la compra no es elegible. "
        f"{result['motivo']} Si necesitas apoyo adicional, podemos escalar tu caso a un agente humano."
    )


def _fallback_general_answer() -> str:
    return (
        "No fue posible usar el modelo generativo en este momento. "
        "Puedes revisar los fragmentos recuperados o intentar nuevamente con Ollama."
    )


def _generate_with_provider(provider: str, prompt: str, temperature: float) -> str:
    if provider == "Open-source local (Ollama)":
        return generate_response_ollama(prompt, temperature=temperature)
    if provider == "Gemini API":
        return generate_response(prompt, temperature=temperature)
    if provider == "Hugging Face API":
        return generate_response_hf(prompt, temperature=temperature)
    raise ValueError(f"Proveedor no soportado: {provider}")


@st.cache_resource(show_spinner=False)
def _get_vector_store_cached(index_version: int):
    return get_vector_store(force_rebuild=index_version > 0)


def _load_vector_store(force_rebuild: bool = False):
    if force_rebuild:
        st.session_state.index_version += 1
    return _get_vector_store_cached(st.session_state.index_version)


st.set_page_config(page_title="EcoMarket RAG Support", page_icon=":seedling:", layout="wide")
st.title("EcoMarket - Sistema RAG para atencion al cliente")
st.caption(
    "Taller practico #2: recuperacion documental con embeddings, ChromaDB y generacion con Ollama, Gemini o Hugging Face."
)

provider = st.sidebar.selectbox(
    "Motor de generacion",
    options=["Open-source local (Ollama)", "Gemini API", "Hugging Face API"],
    index=0,
)
st.sidebar.caption(
    "Generacion recomendada para el taller: Open-source local (Ollama) en local, "
    "o API cloud (Gemini / Hugging Face) para despliegue."
)
st.sidebar.subheader("Configuracion RAG")
st.sidebar.write(f"Embedding model: `{get_embedding_model_name()}`")
st.sidebar.write("Vector store: `ChromaDB`")
st.sidebar.write(f"Top-k por defecto: `{get_rag_top_k()}`")

if "last_request_ts" not in st.session_state:
    st.session_state.last_request_ts = 0.0
if "index_version" not in st.session_state:
    st.session_state.index_version = 0

knowledge_summary = get_knowledge_base_summary()
st.sidebar.write(f"Documentos en knowledge/: `{len(knowledge_summary)}`")

if st.sidebar.button("Reconstruir indice RAG"):
    with st.spinner("Reconstruyendo indice vectorial..."):
        try:
            _load_vector_store(force_rebuild=True)
            st.sidebar.success("Indice RAG reconstruido correctamente.")
        except Exception as error:
            st.sidebar.error(f"No fue posible reconstruir el indice: {error}")


def _cooldown_ready() -> bool:
    elapsed = time.time() - st.session_state.last_request_ts
    if elapsed < REQUEST_COOLDOWN_SECONDS:
        wait = int(REQUEST_COOLDOWN_SECONDS - elapsed) + 1
        st.warning(f"Espera {wait}s antes de enviar otra solicitud.")
        return False
    st.session_state.last_request_ts = time.time()
    return True


tab_general, tab_order, tab_returns, tab_data = st.tabs(
    [
        "Asistente general RAG",
        "Estado de pedido",
        "Gestion de devoluciones",
        "Contexto y evidencias",
    ]
)

with tab_general:
    st.subheader("Consulta abierta sobre EcoMarket")
    st.write(
        "Este flujo recupera fragmentos de la base documental antes de responder. "
        "Si no hay evidencia suficiente, el sistema se abstiene y recomienda escalar a soporte humano."
    )
    question = st.text_area(
        "Pregunta del cliente",
        placeholder=(
            "Ejemplo: Que metodos de pago aceptan? "
            "Puedo devolver un shampoo? "
            "Tienen disponible la botella reutilizable?"
        ),
        height=120,
    )
    top_k = st.slider("Fragmentos a recuperar", min_value=2, max_value=6, value=get_rag_top_k())
    run_general = st.button("Consultar asistente RAG")

    if run_general:
        if not _cooldown_ready():
            st.stop()
        if not question.strip():
            st.warning("Ingresa una pregunta para continuar.")
        else:
            try:
                with st.spinner("Cargando indice vectorial y recuperando contexto..."):
                    vector_store = _load_vector_store()
                    retrieval_results = retrieve_knowledge(question, vector_store=vector_store, k=top_k)
                    retrieved_context = format_retrieved_context(retrieval_results)
                    enough_context = has_sufficient_context(retrieval_results)
                    final_prompt = build_general_rag_prompt(question, retrieved_context) if enough_context else ""
            except Exception as error:
                st.error(f"No fue posible ejecutar el flujo RAG: {error}")
            else:
                if not enough_context:
                    st.warning(
                        "La base de conocimiento no ofrece evidencia suficiente para responder con confianza."
                    )
                    st.write(
                        "No cuento con suficiente informacion en la base de conocimiento de EcoMarket "
                        "para atender esta solicitud. Te recomiendo escalar el caso a soporte humano."
                    )
                else:
                    with st.spinner(f"Generando respuesta con {provider}..."):
                        try:
                            answer = _generate_with_provider(provider, final_prompt, temperature=0.1)
                            st.success("Respuesta generada")
                            st.caption(f"Fuente: {provider}")
                            st.write(answer)
                        except Exception as error:
                            if provider == "Gemini API" and _is_quota_error(error):
                                st.warning(
                                    "La API de Gemini indico limite de uso (cuota 429). "
                                    "Mientras tanto se muestra un respaldo sin generacion."
                                )
                                st.write(_fallback_general_answer())
                            else:
                                st.error(f"No fue posible generar respuesta: {error}")

                sources = sorted(
                    {
                        item["document"].metadata.get("source", "desconocida")
                        for item in retrieval_results
                    }
                )
                st.info(
                    f"Fragmentos recuperados: {len(retrieval_results)} | "
                    f"Fuentes usadas: {', '.join(sources) if sources else 'ninguna'}"
                )
                with st.expander("Ver contexto recuperado"):
                    st.code(retrieved_context)
                if final_prompt:
                    with st.expander("Ver prompt final"):
                        st.code(final_prompt)

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
                    answer = _generate_with_provider(provider, final_prompt, temperature=0.2)
                    st.success("Respuesta generada")
                    st.caption(f"Fuente: {provider}")
                    st.write(answer)
                except Exception as error:
                    if provider == "Gemini API" and _is_quota_error(error):
                        st.warning(
                            "La API de Gemini indico limite de uso (cuota 429). "
                            "Mientras tanto se muestra una respuesta de respaldo generada solo con los datos locales."
                        )
                        st.caption(
                            "Opciones: usa Open-source local (Ollama), espera a que se renueve el cupo "
                            "del free tier o revisa cuotas en Google AI Studio."
                        )
                        st.write(_fallback_order_answer(order, tracking_number))
                    else:
                        st.error(f"No fue posible generar respuesta: {error}")

            with st.expander("Ver contexto recuperado (legacy)"):
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
                answer = _generate_with_provider(provider, final_prompt, temperature=0.2)
                st.success("Respuesta generada")
                st.caption(f"Fuente: {provider}")
                st.write(answer)
            except Exception as error:
                if provider == "Gemini API" and _is_quota_error(error):
                    st.warning(
                        "La API de Gemini indico limite de uso (cuota 429). "
                        "Mientras tanto se muestra una respuesta de respaldo con las politicas locales."
                    )
                    st.caption(
                        "Opciones: usa Ollama en la barra lateral, espera o revisa cuotas en Google AI Studio."
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

        with st.expander("Ver contexto recuperado (legacy)"):
            st.code(policy_context)
        with st.expander("Ver prompt final"):
            st.code(final_prompt)

with tab_data:
    st.subheader("Base de conocimiento del RAG")
    st.json(knowledge_summary)
    st.subheader("Base de pedidos de prueba (legacy)")
    st.json(load_orders())
    st.subheader("Politicas de devolucion (legacy)")
    st.json(load_policies())

st.divider()
st.caption(
    "Nota: el asistente general responde solo con evidencia recuperada. "
    "Los casos sensibles, ambiguos o fuera del alcance de la base documental deben escalarse a soporte humano."
)
