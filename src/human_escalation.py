"""Deteccion de insistencia y escalamiento a agente humano (casos extremos)."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


_INSISTENCE_STEMS = (
    "insisto",
    "no acepto",
    "no estoy de acuerdo",
    "quiero hablar con",
    "hablar con una persona",
    "agente humano",
    "persona real",
    "supervisor",
    "gerente",
    "esto no es justo",
    "exijo",
    "ya te dije",
    "otra vez",
    "no me sirve",
    "pasame con",
    "escalan",
    "escalen",
)

_RETURN_RETRY_STEMS = (
    "devolv",
    "devov",
    "devoc",
    "reembols",
    "reclam",
    "etiqueta",
    "quiero devolver",
)


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.strip())
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn").lower()


def message_signals_insistence(message: str) -> bool:
    text = _normalize(message)
    if not text:
        return False
    if any(stem in text for stem in _INSISTENCE_STEMS):
        return True
    if re.search(r"\b(yo )?insist", text):
        return True
    return False


def message_signals_return_retry(message: str) -> bool:
    text = _normalize(message)
    return any(stem in text for stem in _RETURN_RETRY_STEMS)


@dataclass
class EscalationState:
    """Estado de conversacion para escalamiento (vive en session de Streamlit)."""

    escalated_to_human: bool = False
    return_rejection_count: int = 0
    last_block_reason: str | None = None
    ticket_id: str | None = None

    def to_audit(self) -> dict:
        return {
            "escalated_to_human": self.escalated_to_human,
            "return_rejection_count": self.return_rejection_count,
            "last_block_reason": self.last_block_reason,
            "ticket_id": self.ticket_id,
        }


def register_return_outcome(state: EscalationState, *, blocked: bool, reason: str) -> None:
    if not blocked:
        state.return_rejection_count = 0
        state.last_block_reason = None
        return
    state.return_rejection_count += 1
    state.last_block_reason = reason


def should_escalate_to_human(
    message: str,
    state: EscalationState,
    *,
    is_returns_route: bool,
) -> bool:
    if state.escalated_to_human:
        return is_returns_route
    if state.return_rejection_count < 1:
        return False
    if not is_returns_route:
        return False

    insistence = message_signals_insistence(message)
    retry = message_signals_return_retry(message)

    # Caso extremo: rechazo previo + insistencia explicita
    if insistence:
        return True
    # Segundo intento de devolucion tras un "no" ya comunicado
    if state.return_rejection_count >= 2 and retry:
        return True
    return False


def activate_human_escalation(state: EscalationState) -> str:
    import secrets

    if not state.ticket_id:
        state.ticket_id = f"SUP-{secrets.token_hex(3).upper()}"
    state.escalated_to_human = True
    return state.ticket_id


def format_human_handoff_message(ticket_id: str, *, for_client_view: bool) -> str:
    if for_client_view:
        return (
            "Se ha registrado tu caso con prioridad para revision por un **agente humano**. "
            f"Numero de seguimiento: **{ticket_id}**. "
            "Un asesor te contactara en un plazo maximo de **24 horas habiles** al correo o telefono "
            "asociado a tu pedido. Mientras tanto, no es posible avanzar mas por este canal automatico "
            "con la misma solicitud."
        )
    return (
        "Escalamiento a soporte humano activado por insistencia o reintentos tras un rechazo de politica. "
        f"Ticket: **{ticket_id}**. "
        "Canal sugerido: bandeja de reclamos / chat con agente. "
        "El asistente automatico deja de procesar nuevas solicitudes de devolucion en esta sesion."
    )


def infer_return_blocked_from_response(
    workflow_result,
    audit_log: list[dict],
) -> tuple[bool, str | None]:
    if workflow_result is not None:
        if not workflow_result.elegibilidad.get("elegible"):
            return True, "not_eligible"
        return False, None

    for entry in audit_log:
        status = entry.get("status")
        step = entry.get("step", "")
        if status == "missing_fields":
            return False, None
        if status == "missing_days":
            return False, None
        if step == "returns_workflow" and status == "error":
            return True, "workflow_error"
    return False, None
