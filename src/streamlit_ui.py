"""Componentes compartidos de la interfaz Streamlit (cliente y sustentacion)."""

from __future__ import annotations

import json
import time
from typing import Literal

import streamlit as st

from src.hf_client import generate_response_hf
from src.human_escalation import EscalationState
from src.intent_router import extract_order_id
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
from src.order_service import count_orders_by_state
from src.unified_assistant import run_unified_assistant

AppMode = Literal["client", "demo"]

REQUEST_COOLDOWN_SECONDS = 4
DEFAULT_PROVIDER = "Open-source local (Ollama)"

ROUTE_LABELS = {
    "CONOCIMIENTO": "Consulta sobre la tienda",
    "DEVOLUCION": "Devolucion de producto",
    "PEDIDO": "Estado de pedido",
    "ERROR": "No disponible",
}

EXAMPLE_PROMPTS_DEMO = [
    ("Pagos y facturacion", "Que metodos de pago aceptan?"),
    ("Estado de pedido", "Cual es el estado del pedido 12345?"),
    ("Pedido en transito + devolver", "Pedido 12345 esta en transito y quiero devovlerlo"),
    ("Devolucion entregado", "Quiero devolver el pedido 54321"),
]

EXAMPLE_PROMPTS_CLIENT = [
    ("Medios de pago", "Que metodos de pago aceptan?"),
    ("Seguimiento de pedido", "Quiero saber donde esta mi pedido 12345"),
    ("Devolver un producto", "Necesito devolver un producto del pedido 54321"),
    ("Politica de envios", "Cuanto tarda un envio a Cali?"),
]


def _sk(mode: AppMode, key: str) -> str:
    return f"{mode}_{key}"


def init_session_state(mode: AppMode) -> None:
    if "index_version" not in st.session_state:
        st.session_state.index_version = 0
    if _sk(mode, "last_request_ts") not in st.session_state:
        st.session_state[_sk(mode, "last_request_ts")] = 0.0
    if _sk(mode, "chat_messages") not in st.session_state:
        st.session_state[_sk(mode, "chat_messages")] = []
    if _sk(mode, "pending_prompt") not in st.session_state:
        st.session_state[_sk(mode, "pending_prompt")] = None
    if _sk(mode, "last_order_id") not in st.session_state:
        st.session_state[_sk(mode, "last_order_id")] = None
    if _sk(mode, "escalation") not in st.session_state:
        st.session_state[_sk(mode, "escalation")] = EscalationState()


def _get_escalation_state(mode: AppMode) -> EscalationState:
    key = _sk(mode, "escalation")
    state = st.session_state.get(key)
    if not isinstance(state, EscalationState):
        state = EscalationState()
        st.session_state[key] = state
    return state


def inject_base_styles() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-bottom: 7rem; }
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 0.75rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _is_quota_error(error: Exception) -> bool:
    message = str(error).lower()
    return "429" in message or "quota" in message or "resource_exhausted" in message


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


def load_vector_store(force_rebuild: bool = False):
    if force_rebuild:
        st.session_state.index_version += 1
    return _get_vector_store_cached(st.session_state.index_version)


def _route_label(route_code: str | None) -> str:
    if not route_code:
        return ""
    return ROUTE_LABELS.get(route_code, route_code)


def _order_id_from_audit(audit_log: list | None) -> str | None:
    for entry in audit_log or []:
        order_id = entry.get("order_id")
        if order_id:
            return str(order_id)
    return None


def _handle_unified_message(
    user_prompt: str,
    top_k: int,
    provider: str,
    mode: AppMode,
) -> None:
    messages_key = _sk(mode, "chat_messages")
    st.session_state[messages_key].append({"role": "user", "content": user_prompt})

    try:
        with st.spinner("Un momento, estoy revisando tu solicitud..."):
            vector_store = load_vector_store()
            assistant_result = run_unified_assistant(
                user_prompt,
                vector_store=vector_store,
                generate=lambda prompt, temp: _generate_with_provider(provider, prompt, temp),
                top_k=top_k,
                context_order_id=st.session_state.get(_sk(mode, "last_order_id")),
                escalation=_get_escalation_state(mode),
                for_client_view=(mode == "client"),
            )
        remembered_order_id = _order_id_from_audit(assistant_result.audit_log) or extract_order_id(
            user_prompt
        )
        if remembered_order_id:
            st.session_state[_sk(mode, "last_order_id")] = remembered_order_id
        st.session_state[messages_key].append(
            {
                "role": "assistant",
                "content": assistant_result.answer,
                "route": assistant_result.route.value,
                "audit": assistant_result.audit_log,
            }
        )
    except Exception as error:
        if mode == "client":
            st.session_state[messages_key].append(
                {
                    "role": "assistant",
                    "content": (
                        "No pude completar tu solicitud en este momento. "
                        "Por favor intenta de nuevo en unos segundos o escribe a "
                        "**soporte@ecomarket.co** si el problema continua."
                    ),
                    "route": "ERROR",
                    "audit": [],
                }
            )
            return

        if provider == "Gemini API" and _is_quota_error(error):
            st.session_state[messages_key].append(
                {
                    "role": "assistant",
                    "content": (
                        "El servicio en la nube alcanzo su limite de uso. "
                        "En la barra lateral selecciona **Ollama (local)** e intenta de nuevo."
                    ),
                    "route": "ERROR",
                    "audit": [{"step": "llm", "status": "quota_exceeded"}],
                }
            )
        else:
            st.session_state[messages_key].append(
                {
                    "role": "assistant",
                    "content": (
                        "No pude completar tu solicitud en este momento. "
                        f"Detalle tecnico: {error}"
                    ),
                    "route": "ERROR",
                    "audit": [{"step": "pipeline", "status": "error", "detail": str(error)}],
                }
            )


def _render_chat_history(messages: list[dict], *, show_technical: bool, welcome: str) -> None:
    if not messages:
        with st.chat_message("assistant"):
            st.markdown(welcome)
        return

    for message in messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if not show_technical or message["role"] != "assistant":
                continue
            if message.get("route"):
                st.caption(f"Tema detectado: {_route_label(message['route'])}")
            if message.get("audit"):
                with st.expander("Detalles tecnicos"):
                    st.json(message["audit"])


def _cooldown_ready(mode: AppMode) -> bool:
    ts_key = _sk(mode, "last_request_ts")
    elapsed = time.time() - st.session_state[ts_key]
    if elapsed < REQUEST_COOLDOWN_SECONDS:
        wait = int(REQUEST_COOLDOWN_SECONDS - elapsed) + 1
        st.warning(f"Espera {wait}s antes de enviar otra solicitud.")
        return False
    st.session_state[ts_key] = time.time()
    return True


def _clear_conversation(mode: AppMode) -> None:
    st.session_state[_sk(mode, "chat_messages")] = []
    st.session_state[_sk(mode, "pending_prompt")] = None
    st.session_state[_sk(mode, "last_order_id")] = None
    st.session_state[_sk(mode, "escalation")] = EscalationState()


def render_sidebar_demo() -> tuple[str, int]:
    knowledge_summary = get_knowledge_base_summary()
    st.header("Configuracion")
    provider = st.selectbox(
        "Motor de respuestas",
        options=["Open-source local (Ollama)", "Gemini API", "Hugging Face API"],
        index=0,
        help="Para usar la app en tu PC, deja Ollama y asegurate de tenerlo abierto.",
    )
    if provider == "Open-source local (Ollama)":
        st.success("Modo recomendado: Ollama local")
    else:
        st.warning("Modo en la nube: requiere API key en el archivo .env")

    with st.expander("Opciones avanzadas"):
        top_k = st.slider(
            "Detalle de busqueda en catalogo y politicas",
            min_value=2,
            max_value=6,
            value=get_rag_top_k(),
            help="Solo aplica a preguntas generales sobre la tienda.",
        )
        if st.button("Actualizar base de conocimiento", key="demo_rebuild_index"):
            with st.spinner("Actualizando..."):
                try:
                    load_vector_store(force_rebuild=True)
                    st.success("Base actualizada.")
                except Exception as error:
                    st.error(f"Error: {error}")

    with st.expander("Ejemplos de consulta", expanded=False):
        st.caption("Pulsa un ejemplo; se enviara al chat de Inicio.")
        for index, (label, prompt_text) in enumerate(EXAMPLE_PROMPTS_DEMO):
            if st.button(label, use_container_width=True, key=f"demo_example_{index}"):
                st.session_state[_sk("demo", "pending_prompt")] = prompt_text

    with st.expander("Informacion del sistema"):
        st.caption(
            "Agente con router, herramientas LangChain, RAG con ChromaDB y embeddings multilingues."
        )
        st.write(f"Embedding: `{get_embedding_model_name()}`")
        st.write(f"Documentos indexados: {len(knowledge_summary)}")

    return provider, top_k


def render_sidebar_client() -> int:
    st.header("EcoMarket")
    st.caption("Atencion al cliente en linea")
    with st.expander("Preguntas frecuentes"):
        st.markdown(
            """
            - **Pedidos:** indica tu numero de pedido (ej. 12345).
            - **Devoluciones:** describe el producto y el motivo.
            - **Pagos y envios:** pregunta con tus propias palabras.
            """
        )
    with st.expander("Ejemplos rapidos"):
        for index, (label, prompt_text) in enumerate(EXAMPLE_PROMPTS_CLIENT):
            if st.button(label, use_container_width=True, key=f"client_example_{index}"):
                st.session_state[_sk("client", "pending_prompt")] = prompt_text
    return get_rag_top_k()


def render_chat_page(
    mode: AppMode,
    *,
    provider: str,
    top_k: int,
    show_technical: bool,
    welcome: str,
    input_placeholder: str,
    header_caption: str | None,
) -> None:
    init_session_state(mode)
    messages = st.session_state[_sk(mode, "chat_messages")]

    header_left, header_right = st.columns([5, 1])
    with header_left:
        if header_caption:
            st.caption(header_caption)
    with header_right:
        if st.button("Nueva conversacion", use_container_width=True, key=f"{mode}_new_chat"):
            _clear_conversation(mode)
            st.rerun()

    chat_history = st.container(height=520, border=False)
    with chat_history:
        _render_chat_history(messages, show_technical=show_technical, welcome=welcome)

    prompt_from_input = st.chat_input(input_placeholder, key=f"{mode}_chat_input")
    prompt_to_run = prompt_from_input or st.session_state.get(_sk(mode, "pending_prompt"))

    if prompt_to_run:
        st.session_state[_sk(mode, "pending_prompt")] = None
        if not _cooldown_ready(mode):
            st.stop()
        _handle_unified_message(prompt_to_run.strip(), top_k, provider, mode)
        st.rerun()


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


def render_demo_guide_tab() -> None:
    st.markdown(
        """
        ### Guia rapida (3 pasos)

        1. **Abre Ollama** en tu computador (icono en la bandeja de Windows).
        2. En la barra lateral deja seleccionado **Ollama (local)**.
        3. En la pestana **Inicio**, escribe abajo en el chat o elige un ejemplo en la barra lateral.

        ### Que puedes preguntar

        | Si necesitas... | Escribe algo como... |
        |-----------------|----------------------|
        | Medios de pago | `Que metodos de pago aceptan?` |
        | Precio de un producto | `Cuanto cuesta el cafe organico 500g?` |
        | Tu pedido | `Estado del pedido 12345` |
        | Devolver ropa | `Quiero devolver una camiseta, compre hace 10 dias` |
        | Devolver higiene | `Quiero devolver un shampoo, compre hace 5 dias` |

        ### Consejos para devoluciones

        - Menciona el **tipo de producto** (ropa, accesorios, higiene, perecederos).
        - Indica **cuantos dias** pasaron desde la compra (ejemplo: *hace 10 dias*).
        - Si el caso es elegible, recibiras una **etiqueta simulada** con enlace de descarga.

        ### Numeros de pedido de prueba

        - **En transito + devolucion:** `12345`.
        - **Entregado + devolucion con etiqueta:** `54321`.
        - **Escalamiento humano:** probar shampoo no elegible y luego escribir *insisto en la devolucion*.
        - Base sintetica: `10001` - `10100`.
        """
    )


def render_demo_tech_panel(provider: str) -> None:
    knowledge_summary = get_knowledge_base_summary()
    st.caption("Vistas del Taller 2 y diagnostico para sustentacion academica.")
    tech_general, tech_order, tech_returns, tech_data = st.tabs(
        ["RAG aislado", "Pedido (legacy)", "Devoluciones (legacy)", "Datos"]
    )

    with tech_general:
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
        run_general = st.button("Consultar asistente RAG", key="demo_rag_run")

        if run_general:
            if not _cooldown_ready("demo"):
                st.stop()
            if not question.strip():
                st.warning("Ingresa una pregunta para continuar.")
            else:
                try:
                    with st.spinner("Cargando indice vectorial y recuperando contexto..."):
                        vector_store = load_vector_store()
                        retrieval_results = retrieve_knowledge(
                            question, vector_store=vector_store, k=top_k
                        )
                        retrieved_context = format_retrieved_context(retrieval_results)
                        enough_context = has_sufficient_context(retrieval_results)
                        final_prompt = (
                            build_general_rag_prompt(question, retrieved_context)
                            if enough_context
                            else ""
                        )
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
                                answer = _generate_with_provider(provider, final_prompt, 0.1)
                                st.success("Respuesta generada")
                                st.caption(f"Fuente: {provider}")
                                st.write(answer)
                            except Exception as error:
                                if provider == "Gemini API" and _is_quota_error(error):
                                    st.warning("Cuota Gemini agotada; respaldo sin generacion.")
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

    with tech_order:
        st.subheader("Consulta de estado de pedido")
        tracking_number = st.text_input("Numero de pedido", placeholder="Ejemplo: 12345")
        run_order = st.button("Consultar estado", key="demo_order_run")

        if run_order:
            if not _cooldown_ready("demo"):
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
                        answer = _generate_with_provider(provider, final_prompt, 0.2)
                        st.success("Respuesta generada")
                        st.caption(f"Fuente: {provider}")
                        st.write(answer)
                    except Exception as error:
                        if provider == "Gemini API" and _is_quota_error(error):
                            st.warning("Cuota Gemini agotada; respaldo con datos locales.")
                            st.write(_fallback_order_answer(order, tracking_number))
                        else:
                            st.error(f"No fue posible generar respuesta: {error}")
                with st.expander("Ver contexto recuperado (legacy)"):
                    st.code(order_context)
                with st.expander("Ver prompt final"):
                    st.code(final_prompt)

    with tech_returns:
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
        run_return = st.button("Evaluar devolucion", key="demo_returns_run")

        if run_return:
            if not _cooldown_ready("demo"):
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
                    answer = _generate_with_provider(provider, final_prompt, 0.2)
                    st.success("Respuesta generada")
                    st.caption(f"Fuente: {provider}")
                    st.write(answer)
                except Exception as error:
                    if provider == "Gemini API" and _is_quota_error(error):
                        st.warning("Cuota Gemini agotada; respaldo con politicas locales.")
                        st.write(
                            _fallback_return_answer(result, category, int(days_since_purchase))
                        )
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

    with tech_data:
        st.subheader("Base de conocimiento del RAG")
        st.json(knowledge_summary)
        st.subheader("Base de pedidos sinteticos")
        st.write(f"Total pedidos: {len(load_orders())}")
        st.json(count_orders_by_state())
        with st.expander("Ver todos los pedidos"):
            st.json(load_orders())
        st.subheader("Politicas de devolucion (legacy)")
        st.json(load_policies())
