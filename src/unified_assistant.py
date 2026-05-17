"""Asistente unificado: router + RAG + workflow de devoluciones."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

from langchain_community.vectorstores import Chroma

from src.intent_router import AssistantRoute, classify_route, extract_order_id, extract_return_slots
from src.rag_engine import (
    PROMPTS_DIR,
    build_general_rag_prompt,
    find_order,
    format_retrieved_context,
    has_sufficient_context,
    retrieve_knowledge,
)
from src.human_escalation import (
    EscalationState,
    activate_human_escalation,
    format_human_handoff_message,
    infer_return_blocked_from_response,
    register_return_outcome,
    should_escalate_to_human,
)
from src.order_service import enrich_return_slots_from_order, format_order_status_answer
from src.returns_workflow import (
    ReturnsWorkflowResult,
    audit_to_dict,
    format_returns_fallback,
    run_returns_workflow,
    validate_return_slots,
)


GenerateFn = Callable[[str, float], str]

_LLM_REFUSAL_MARKERS = (
    "no puedo generar",
    "cumpla con todas las reglas",
    "cumplir con las reglas",
    "no puedo cumplir",
    "no puedo responder",
)


def _is_meta_refusal(answer: str) -> bool:
    lower = answer.strip().lower()
    return any(marker in lower for marker in _LLM_REFUSAL_MARKERS)


def _fallback_knowledge_answer(message: str, retrieved_context: str) -> str:
    if "pedido" in message.lower() or "orden" in message.lower():
        return (
            "Con gusto te ayudo con tu pedido. "
            "Indicame el numero de pedido (por ejemplo 12345 o 54321) "
            "y te confirmo el estado, envio o opciones de devolucion."
        )
    snippet = retrieved_context.strip().replace("\n\n", " ")[:400]
    if snippet and snippet != "Sin contexto recuperado.":
        return (
            "Segun la informacion disponible de EcoMarket: "
            f"{snippet} "
            "Si necesitas mas detalle, puedo escalar tu caso a un agente humano."
        )
    return (
        "Puedo ayudarte con pagos, envios, productos y politicas de EcoMarket. "
        "Se mas especifico en tu pregunta o indica tu numero de pedido si aplica."
    )


@dataclass
class AssistantResponse:
    route: AssistantRoute
    answer: str
    audit_log: list[dict[str, Any]] = field(default_factory=list)
    retrieved_context: str = ""
    final_prompt: str = ""
    workflow_result: ReturnsWorkflowResult | None = None
    sources: list[str] = field(default_factory=list)
    used_llm: bool = True


def _read_returns_agent_prompt() -> str:
    path = PROMPTS_DIR / "returns_agent_prompt.md"
    with path.open("r", encoding="utf-8") as file:
        return file.read()


def _build_returns_prompt(user_message: str, workflow: ReturnsWorkflowResult) -> str:
    tool_payload = {
        "consulta_pedido": workflow.consulta_pedido,
        "elegibilidad": workflow.elegibilidad,
        "etiqueta": workflow.etiqueta,
        "reembolso": workflow.reembolso,
        "categoria": workflow.categoria,
        "dias_desde_compra": workflow.dias_desde_compra,
        "id_pedido": workflow.id_pedido,
    }
    template = _read_returns_agent_prompt()
    return template.format(
        user_message=user_message.strip(),
        tool_results=json.dumps(tool_payload, ensure_ascii=False, indent=2),
    )


def _run_knowledge_route(
    message: str,
    vector_store: Chroma,
    top_k: int,
    generate: GenerateFn,
    temperature: float = 0.1,
) -> AssistantResponse:
    retrieval_results = retrieve_knowledge(message, vector_store=vector_store, k=top_k)
    retrieved_context = format_retrieved_context(retrieval_results)
    sources = sorted(
        {item["document"].metadata.get("source", "desconocida") for item in retrieval_results}
    )

    if not has_sufficient_context(retrieval_results):
        return AssistantResponse(
            route=AssistantRoute.KNOWLEDGE,
            answer=(
                "No cuento con suficiente informacion en la base de conocimiento de EcoMarket "
                "para responder esta solicitud con confianza. Te recomiendo escalar el caso a soporte humano."
            ),
            audit_log=[{"step": "rag_retrieval", "status": "insufficient_context"}],
            retrieved_context=retrieved_context,
            sources=sources,
            used_llm=False,
        )

    final_prompt = build_general_rag_prompt(message, retrieved_context)
    audit_log = [
        {"step": "rag_retrieval", "status": "ok", "fragments": len(retrieval_results)},
    ]
    try:
        answer = generate(final_prompt, temperature)
        if _is_meta_refusal(answer):
            answer = _fallback_knowledge_answer(message, retrieved_context)
            audit_log.append({"step": "llm_response", "status": "meta_refusal_replaced"})
            used_llm = False
        else:
            audit_log.append({"step": "llm_response", "status": "ok"})
            used_llm = True
    except Exception as error:
        answer = _fallback_knowledge_answer(message, retrieved_context)
        audit_log.append({"step": "llm_response", "status": "error", "detail": str(error)})
        used_llm = False

    return AssistantResponse(
        route=AssistantRoute.KNOWLEDGE,
        answer=answer,
        audit_log=audit_log,
        retrieved_context=retrieved_context,
        final_prompt=final_prompt,
        sources=sources,
        used_llm=used_llm,
    )


def _run_order_route(
    message: str,
    generate: GenerateFn,
    temperature: float = 0.2,
) -> AssistantResponse:
    order_id = extract_order_id(message)
    if not order_id:
        return AssistantResponse(
            route=AssistantRoute.ORDER_STATUS,
            answer=(
                "Hola, con gusto te ayudo con tu pedido. "
                "Indicame el **numero de pedido** (por ejemplo `12345`, `54321` o `10042`) "
                "y te informo el estado y el seguimiento."
            ),
            audit_log=[{"step": "order_lookup", "status": "missing_order_id"}],
            used_llm=False,
        )

    order = find_order(order_id)
    audit_log = [
        {
            "step": "order_lookup",
            "status": "ok",
            "order_id": order_id,
            "found": order is not None,
        },
    ]

    if order is None:
        return AssistantResponse(
            route=AssistantRoute.ORDER_STATUS,
            answer=(
                f"No encontre el pedido **{order_id}**. "
                "Verifica el numero e intentalo de nuevo."
            ),
            audit_log=audit_log,
            used_llm=False,
        )

    # Respuesta directa desde datos del pedido (evita alucinaciones de Ollama)
    answer = format_order_status_answer(order)
    audit_log.append({"step": "order_response", "status": "template_from_db"})

    return AssistantResponse(
        route=AssistantRoute.ORDER_STATUS,
        answer=answer,
        audit_log=audit_log,
        final_prompt="",
        used_llm=False,
    )


def _run_returns_route(
    message: str,
    generate: GenerateFn,
    temperature: float = 0.2,
    context_order_id: str | None = None,
) -> AssistantResponse:
    slots = extract_return_slots(message)
    order_id = slots.get("id_pedido") or context_order_id
    missing = validate_return_slots(
        slots["categoria"],
        slots["dias_desde_compra"],
        id_pedido=order_id,
        context_order_id=context_order_id,
    )
    if missing:
        needed = ", ".join(missing)
        return AssistantResponse(
            route=AssistantRoute.RETURNS,
            answer=(
                f"Para gestionar tu devolucion o reclamo necesito: {needed}. "
                "Ejemplo: pedido 12345 quiero devolverlo. "
                "O: devolver camiseta de ropa, compre hace 10 dias."
            ),
            audit_log=[{"step": "slot_extraction", "status": "missing_fields", "fields": missing}],
            used_llm=False,
        )

    enriched = enrich_return_slots_from_order(
        order_id,
        slots["categoria"],
        slots["dias_desde_compra"],
    )
    categoria = str(enriched["categoria"])
    dias_value = enriched["dias_desde_compra"]
    if dias_value is None:
        return AssistantResponse(
            route=AssistantRoute.RETURNS,
            answer=(
                "Indica los dias desde la compra o un numero de pedido valido "
                "para calcular la elegibilidad."
            ),
            audit_log=[{"step": "slot_extraction", "status": "missing_days"}],
            used_llm=False,
        )
    dias = int(dias_value)
    order_id = enriched.get("id_pedido")

    try:
        workflow = run_returns_workflow(categoria, dias, id_pedido=order_id)
    except Exception as error:
        return AssistantResponse(
            route=AssistantRoute.RETURNS,
            answer=(
                "No pude completar la verificacion de devolucion por un error interno. "
                f"Detalle: {error}. Intenta de nuevo o contacta a soporte humano."
            ),
            audit_log=[{"step": "returns_workflow", "status": "error", "detail": str(error)}],
            used_llm=False,
        )

    audit_log = audit_to_dict(workflow.audit)

    try:
        final_prompt = _build_returns_prompt(message, workflow)
        answer = generate(final_prompt, temperature)
        if _is_meta_refusal(answer):
            answer = format_returns_fallback(workflow)
            used_llm = False
            audit_log.append({"step": "llm_response", "status": "meta_refusal_replaced"})
        else:
            used_llm = True
            audit_log.append({"step": "llm_response", "status": "ok"})
    except Exception as error:
        answer = format_returns_fallback(workflow)
        final_prompt = ""
        used_llm = False
        audit_log.append({"step": "llm_response", "status": "error", "detail": str(error)})

    return AssistantResponse(
        route=AssistantRoute.RETURNS,
        answer=answer,
        audit_log=audit_log,
        final_prompt=final_prompt,
        workflow_result=workflow,
        used_llm=used_llm,
    )


def _human_escalation_response(
    ticket_id: str,
    *,
    for_client_view: bool,
    trigger: str,
) -> AssistantResponse:
    return AssistantResponse(
        route=AssistantRoute.RETURNS,
        answer=format_human_handoff_message(ticket_id, for_client_view=for_client_view),
        audit_log=[
            {
                "step": "human_escalation",
                "status": "activated",
                "ticket_id": ticket_id,
                "trigger": trigger,
            }
        ],
        used_llm=False,
    )


def run_unified_assistant(
    message: str,
    vector_store: Chroma,
    generate: GenerateFn,
    top_k: int = 4,
    context_order_id: str | None = None,
    escalation: EscalationState | None = None,
    for_client_view: bool = False,
) -> AssistantResponse:
    route = classify_route(message)
    is_returns = route == AssistantRoute.RETURNS

    if escalation is not None:
        if escalation.escalated_to_human and is_returns:
            ticket_id = escalation.ticket_id or activate_human_escalation(escalation)
            return _human_escalation_response(
                ticket_id,
                for_client_view=for_client_view,
                trigger="session_already_escalated",
            )

        if should_escalate_to_human(message, escalation, is_returns_route=is_returns):
            ticket_id = activate_human_escalation(escalation)
            trigger = (
                "insistence_after_rejection"
                if escalation.return_rejection_count >= 1
                else "repeated_return_attempts"
            )
            return _human_escalation_response(
                ticket_id,
                for_client_view=for_client_view,
                trigger=trigger,
            )

    if route == AssistantRoute.RETURNS:
        response = _run_returns_route(message, generate, context_order_id=context_order_id)
        if escalation is not None:
            blocked, reason = infer_return_blocked_from_response(
                response.workflow_result,
                response.audit_log,
            )
            if blocked and reason:
                register_return_outcome(escalation, blocked=True, reason=reason)
            elif response.workflow_result is not None:
                register_return_outcome(escalation, blocked=False, reason="")
            response.audit_log.append({"step": "escalation_state", **escalation.to_audit()})
        return response
    if route == AssistantRoute.ORDER_STATUS:
        return _run_order_route(message, generate)
    return _run_knowledge_route(message, vector_store, top_k, generate)
