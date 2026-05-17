"""Workflow explicito de devoluciones con herramientas LangChain."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from src.agent_tools import (
    consultar_pedido_para_reclamo,
    generar_etiqueta_devolucion,
    generar_solicitud_reembolso,
    verificar_elegibilidad_producto,
)
from src.order_service import enrich_return_slots_from_order


@dataclass
class WorkflowAuditEntry:
    step: str
    tool: str | None
    input: dict[str, Any]
    output: Any
    status: str


@dataclass
class ReturnsWorkflowResult:
    categoria: str
    dias_desde_compra: int
    id_pedido: str
    elegibilidad: dict[str, Any]
    etiqueta: dict[str, Any] | None
    reembolso: dict[str, Any] | None
    consulta_pedido: dict[str, Any] | None
    audit: list[WorkflowAuditEntry] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)


def run_returns_workflow(
    categoria: str,
    dias_desde_compra: int,
    id_pedido: str | None = None,
) -> ReturnsWorkflowResult:
    audit: list[WorkflowAuditEntry] = []
    order_ref = (id_pedido or "SIN_PEDIDO").strip()
    consulta_pedido: dict[str, Any] | None = None

    if id_pedido:
        consult_input = {"id_pedido": order_ref}
        raw_consult = consultar_pedido_para_reclamo.invoke(consult_input)
        consulta_pedido = json.loads(raw_consult)
        audit.append(
            WorkflowAuditEntry(
                step="consultar_pedido",
                tool="consultar_pedido_para_reclamo",
                input=consult_input,
                output=consulta_pedido,
                status="ok" if consulta_pedido.get("encontrado") else "not_found",
            )
        )
        if not consulta_pedido.get("encontrado"):
            return ReturnsWorkflowResult(
                categoria=categoria,
                dias_desde_compra=dias_desde_compra,
                id_pedido=order_ref,
                elegibilidad={
                    "elegible": False,
                    "motivo": consulta_pedido.get("motivo", "Pedido no encontrado."),
                    "instrucciones": [],
                },
                etiqueta=None,
                reembolso=None,
                consulta_pedido=consulta_pedido,
                audit=audit,
            )

    tool_input = {
        "categoria": categoria,
        "dias_desde_compra": dias_desde_compra,
        "id_pedido": order_ref if id_pedido else "",
    }
    try:
        raw_eligibility = verificar_elegibilidad_producto.invoke(tool_input)
        eligibility = json.loads(raw_eligibility)
        audit.append(
            WorkflowAuditEntry(
                step="verificar_elegibilidad",
                tool="verificar_elegibilidad_producto",
                input=tool_input,
                output=eligibility,
                status="ok",
            )
        )
    except Exception as error:
        audit.append(
            WorkflowAuditEntry(
                step="verificar_elegibilidad",
                tool="verificar_elegibilidad_producto",
                input=tool_input,
                output=str(error),
                status="error",
            )
        )
        raise

    etiqueta: dict[str, Any] | None = None
    reembolso: dict[str, Any] | None = None

    if eligibility.get("puede_generar_etiqueta"):
        label_input = {"categoria": categoria, "id_pedido": order_ref}
        raw_label = generar_etiqueta_devolucion.invoke(label_input)
        etiqueta = json.loads(raw_label)
        audit.append(
            WorkflowAuditEntry(
                step="generar_etiqueta",
                tool="generar_etiqueta_devolucion",
                input=label_input,
                output=etiqueta,
                status="ok" if "label_id" in etiqueta else "error",
            )
        )
    elif eligibility.get("puede_solicitar_reembolso") and id_pedido:
        refund_input = {
            "id_pedido": order_ref,
            "motivo": "Cliente solicita devolucion o cancelacion del pedido",
        }
        raw_refund = generar_solicitud_reembolso.invoke(refund_input)
        reembolso = json.loads(raw_refund)
        audit.append(
            WorkflowAuditEntry(
                step="generar_reembolso",
                tool="generar_solicitud_reembolso",
                input=refund_input,
                output=reembolso,
                status="ok" if "ticket_id" in reembolso else "error",
            )
        )

    return ReturnsWorkflowResult(
        categoria=categoria,
        dias_desde_compra=dias_desde_compra,
        id_pedido=order_ref,
        elegibilidad=eligibility,
        etiqueta=etiqueta,
        reembolso=reembolso,
        consulta_pedido=consulta_pedido,
        audit=audit,
    )


def validate_return_slots(
    categoria: str | None,
    dias_desde_compra: int | None,
    id_pedido: str | None = None,
    context_order_id: str | None = None,
) -> list[str]:
    effective_order_id = id_pedido or context_order_id
    enriched = enrich_return_slots_from_order(effective_order_id, categoria, dias_desde_compra)
    missing: list[str] = []
    if not enriched.get("categoria") and not effective_order_id:
        missing.append("categoria del producto (perecederos, higiene, ropa o accesorios)")
    if enriched.get("dias_desde_compra") is None and not effective_order_id:
        missing.append("dias desde la compra o numero de pedido")
    if effective_order_id and enriched.get("order") is None:
        missing.append("numero de pedido valido (verifica el ID)")
    return missing


def format_returns_fallback(result: ReturnsWorkflowResult) -> str:
    eligibility = result.elegibilidad
    if result.reembolso and result.reembolso.get("ticket_id"):
        return (
            f"{result.reembolso.get('mensaje', '')} "
            f"Ticket de reembolso: {result.reembolso['ticket_id']} "
            f"para el pedido {result.id_pedido}."
        )

    if not eligibility.get("elegible") and not eligibility.get("puede_solicitar_reembolso"):
        return (
            f"Tu solicitud para la categoria {result.categoria} con "
            f"{result.dias_desde_compra} dias desde la compra no es elegible. "
            f"{eligibility.get('motivo', '')} "
            "Si necesitas apoyo adicional, podemos escalar tu caso a un agente humano."
        )

    label = result.etiqueta or {}
    if label.get("label_id"):
        instructions = " ".join(
            f"{idx + 1}) {step}"
            for idx, step in enumerate(eligibility.get("instrucciones", []))
        )
        return (
            f"Tu devolucion para el pedido {result.id_pedido} es elegible. "
            f"{eligibility.get('motivo', '')} "
            f"Etiqueta {label.get('label_id')}: descarga en {label.get('url_descarga', 'N/A')}. "
            f"Pasos: {instructions}"
        )

    return (
        f"{eligibility.get('motivo', 'Procesamos tu solicitud.')} "
        f"Pedido: {result.id_pedido}."
    )


def audit_to_dict(audit: list[WorkflowAuditEntry]) -> list[dict[str, Any]]:
    return [
        {
            "step": entry.step,
            "tool": entry.tool,
            "input": entry.input,
            "output": entry.output,
            "status": entry.status,
        }
        for entry in audit
    ]
