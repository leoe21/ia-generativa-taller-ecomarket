"""Herramientas LangChain simuladas para pedidos, reclamos y devoluciones."""

from __future__ import annotations

import json
import secrets
from datetime import datetime, timezone
from typing import Any

from langchain_core.tools import tool

from src.order_service import build_order_context, evaluate_return_with_order, get_order_by_id
from src.rag_engine import classify_return

_LABEL_REGISTRY: dict[str, dict[str, Any]] = {}
_REFUND_REGISTRY: dict[str, dict[str, Any]] = {}
_VALID_CATEGORIES = frozenset({"perecederos", "higiene", "ropa", "accesorios"})


@tool
def consultar_pedido_para_reclamo(id_pedido: str) -> str:
    """Consulta un pedido por ID y resume si aplica devolucion fisica o reclamo de reembolso.

    Args:
        id_pedido: Numero de pedido (ej. 12345, 10042).

    Returns:
        JSON con datos del pedido y acciones permitidas.
    """
    order = get_order_by_id(id_pedido)
    if order is None:
        return json.dumps(
            {
                "encontrado": False,
                "id_pedido": id_pedido.strip(),
                "motivo": "No existe un pedido con ese numero en el sistema.",
            },
            ensure_ascii=False,
        )

    category = str(order.get("categoria_producto", "ropa"))
    days = int(order.get("dias_desde_compra", 0))
    evaluation = evaluate_return_with_order(category, days, order)
    payload = {
        "encontrado": True,
        "id_pedido": order["id_pedido"],
        "estado": order.get("estado"),
        "estado_envio": order.get("estado_envio"),
        "categoria_producto": category,
        "dias_desde_compra": days,
        "resumen": build_order_context(order),
        "acciones": {
            "puede_generar_etiqueta": evaluation.get("puede_generar_etiqueta", False),
            "puede_solicitar_reembolso": evaluation.get("puede_solicitar_reembolso", False),
        },
        "evaluacion_previa": evaluation,
    }
    return json.dumps(payload, ensure_ascii=False)


@tool
def verificar_elegibilidad_producto(
    categoria: str,
    dias_desde_compra: int,
    id_pedido: str = "",
) -> str:
    """Verifica elegibilidad de devolucion o reclamo segun categoria, dias y estado del pedido.

    Args:
        categoria: perecederos, higiene, ropa o accesorios.
        dias_desde_compra: Dias desde la compra.
        id_pedido: Opcional. Si se envia, se valida contra el estado logistico del pedido.

    Returns:
        JSON con elegible, motivo, instrucciones y flags de etiqueta/reembolso.
    """
    category_clean = categoria.strip().lower()
    days = int(dias_desde_compra)
    order = get_order_by_id(id_pedido) if id_pedido.strip() else None

    if order:
        category_clean = str(order.get("categoria_producto", category_clean)).lower()
        if order.get("dias_desde_compra") is not None:
            days = int(order["dias_desde_compra"])

    if category_clean not in _VALID_CATEGORIES:
        payload = {
            "categoria": category_clean,
            "dias_desde_compra": days,
            "elegible": False,
            "motivo": "Categoria no valida. Usa: perecederos, higiene, ropa o accesorios.",
            "instrucciones": [],
            "error": "categoria_invalida",
            "id_pedido": id_pedido or None,
        }
        return json.dumps(payload, ensure_ascii=False)

    if days < 0 or days > 365:
        payload = {
            "categoria": category_clean,
            "dias_desde_compra": days,
            "elegible": False,
            "motivo": "El numero de dias debe estar entre 0 y 365.",
            "instrucciones": [],
            "error": "dias_invalidos",
            "id_pedido": id_pedido or None,
        }
        return json.dumps(payload, ensure_ascii=False)

    if order:
        result = evaluate_return_with_order(category_clean, days, order)
    else:
        base = classify_return(category_clean, days)
        result = {
            **base,
            "tipo_gestion": "solo_politica_categoria",
            "puede_generar_etiqueta": base.get("elegible", False),
            "puede_solicitar_reembolso": base.get("elegible", False),
            "estado_envio": None,
            "id_pedido": None,
        }

    payload = {
        "categoria": category_clean,
        "dias_desde_compra": days,
        **result,
    }
    return json.dumps(payload, ensure_ascii=False)


@tool
def generar_etiqueta_devolucion(categoria: str, id_pedido: str = "SIN_PEDIDO") -> str:
    """Genera etiqueta de devolucion fisica (solo pedidos entregados y elegibles).

    Args:
        categoria: Categoria del producto.
        id_pedido: ID del pedido.

    Returns:
        JSON con label_id y url_descarga.
    """
    category_clean = categoria.strip().lower()
    order = get_order_by_id(id_pedido)
    if order and not order.get("permite_devolucion_fisica", False):
        return json.dumps(
            {
                "error": "estado_no_permite_etiqueta",
                "motivo": (
                    f"El pedido {id_pedido} no esta entregado; usa solicitud de reembolso "
                    "en lugar de etiqueta de devolucion."
                ),
            },
            ensure_ascii=False,
        )

    label_id = f"RET-{secrets.token_hex(4).upper()}"
    created_at = datetime.now(timezone.utc).isoformat()
    url = f"https://returns.ecomarket.co/label/{label_id}"

    record = {
        "label_id": label_id,
        "url_descarga": url,
        "categoria": category_clean,
        "id_pedido": id_pedido.strip() or "SIN_PEDIDO",
        "created_at": created_at,
        "estado": "generada",
    }
    _LABEL_REGISTRY[label_id] = record
    return json.dumps(record, ensure_ascii=False)


@tool
def generar_solicitud_reembolso(id_pedido: str, motivo: str = "Solicitud del cliente") -> str:
    """Registra solicitud de reembolso para pedidos en transito o no elegibles para etiqueta.

    Args:
        id_pedido: Numero de pedido.
        motivo: Motivo breve del reclamo.

    Returns:
        JSON con ticket de reembolso simulado.
    """
    order = get_order_by_id(id_pedido)
    if order is None:
        return json.dumps(
            {"error": "pedido_no_encontrado", "id_pedido": id_pedido},
            ensure_ascii=False,
        )

    ticket_id = f"RMB-{secrets.token_hex(4).upper()}"
    record = {
        "ticket_id": ticket_id,
        "id_pedido": order["id_pedido"],
        "estado": "en_revision",
        "motivo": motivo.strip() or "Solicitud del cliente",
        "estado_pedido": order.get("estado"),
        "monto_cop": order.get("monto_cop"),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mensaje": (
            "Tu solicitud de reembolso fue registrada. Recibiras actualizacion por correo "
            "en 24-48 horas habiles."
        ),
    }
    _REFUND_REGISTRY[ticket_id] = record
    return json.dumps(record, ensure_ascii=False)


def get_label_registry() -> dict[str, dict[str, Any]]:
    return dict(_LABEL_REGISTRY)


def get_refund_registry() -> dict[str, dict[str, Any]]:
    return dict(_REFUND_REGISTRY)
