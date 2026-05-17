"""Logica de pedidos, reclamos y devoluciones ligadas a id_pedido."""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.rag_engine import classify_return, find_order, load_orders


def get_order_by_id(order_id: str) -> Optional[Dict[str, Any]]:
    return find_order(order_id.strip())


def enrich_return_slots_from_order(
    order_id: str | None,
    categoria: str | None,
    dias_desde_compra: int | None,
) -> dict[str, Any]:
    """Completa categoria/dias desde el pedido si el usuario no los escribio."""
    order = get_order_by_id(order_id) if order_id else None
    if order is None:
        return {
            "order": None,
            "categoria": categoria,
            "dias_desde_compra": dias_desde_compra,
            "id_pedido": order_id,
        }

    resolved_category = categoria or order.get("categoria_producto")
    resolved_days = dias_desde_compra
    if resolved_days is None and order.get("dias_desde_compra") is not None:
        resolved_days = int(order["dias_desde_compra"])

    return {
        "order": order,
        "categoria": resolved_category,
        "dias_desde_compra": resolved_days,
        "id_pedido": order.get("id_pedido", order_id),
    }


def evaluate_return_with_order(
    categoria: str,
    dias_desde_compra: int,
    order: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Combina politica de categoria con estado logistico del pedido."""
    policy = classify_return(categoria, dias_desde_compra)

    if order is None:
        return {
            **policy,
            "tipo_gestion": "solo_politica_categoria",
            "puede_generar_etiqueta": policy.get("elegible", False),
            "puede_solicitar_reembolso": policy.get("elegible", False),
            "estado_envio": None,
        }

    estado_envio = order.get("estado_envio", "desconocido")
    permite_fisica = bool(order.get("permite_devolucion_fisica", False))
    permite_reclamo = bool(order.get("permite_reclamo_reembolso", True))

    if estado_envio != "entregado":
        if permite_reclamo:
            return {
                "elegible": True,
                "motivo": (
                    f"El pedido {order['id_pedido']} esta en estado '{order.get('estado')}'. "
                    "No aplica devolucion fisica con etiqueta, pero puedes solicitar "
                    "cancelacion o reembolso mientras el envio no se ha entregado."
                ),
                "instrucciones": [
                    "Confirma el numero de pedido con soporte.",
                    "Se abrira un caso de reembolso sin etiqueta de devolucion.",
                    "Recibiras respuesta por correo en 24-48 horas habiles.",
                ],
                "tipo_gestion": "reclamo_reembolso",
                "puede_generar_etiqueta": False,
                "puede_solicitar_reembolso": True,
                "estado_envio": estado_envio,
                "id_pedido": order["id_pedido"],
            }
        return {
            "elegible": False,
            "motivo": (
                f"El pedido {order['id_pedido']} no permite reclamos automaticos "
                f"en estado '{order.get('estado')}'."
            ),
            "instrucciones": [],
            "tipo_gestion": "no_permitido",
            "puede_generar_etiqueta": False,
            "puede_solicitar_reembolso": False,
            "estado_envio": estado_envio,
            "id_pedido": order["id_pedido"],
        }

    # entregado: politica de categoria + etiqueta si aplica
    puede_etiqueta = policy.get("elegible", False) and permite_fisica
    return {
        **policy,
        "tipo_gestion": "devolucion_entregado" if puede_etiqueta else "reclamo_post_entrega",
        "puede_generar_etiqueta": puede_etiqueta,
        "puede_solicitar_reembolso": policy.get("elegible", False) and permite_reclamo,
        "estado_envio": estado_envio,
        "id_pedido": order["id_pedido"],
    }


def build_order_context(order: Optional[Dict[str, Any]]) -> str:
    if order is None:
        return "No se encontro informacion para ese numero de pedido."
    return (
        f"ID_PEDIDO: {order['id_pedido']} | Estado: {order.get('estado')} | "
        f"Estado envio: {order.get('estado_envio', 'N/A')} | "
        f"Categoria: {order.get('categoria_producto', 'N/A')} | "
        f"Dias desde compra: {order.get('dias_desde_compra', 'N/A')} | "
        f"Monto COP: {order.get('monto_cop', 'N/A')} | "
        f"URL_TRACKING: {order.get('tracking_url')} | "
        f"RETRASADO: {order.get('retrasado', False)}"
    )


def format_order_status_answer(order: Dict[str, Any]) -> str:
    """Respuesta determinista para consulta de pedido (sin alucinaciones del LLM)."""
    estado = order.get("estado", "desconocido")
    estado_envio = order.get("estado_envio", "desconocido")
    dias = order.get("dias_desde_compra", "N/A")
    categoria = order.get("categoria_producto", "N/A")
    cliente = order.get("cliente", "cliente")
    tracking = order.get("tracking_url", "")
    fecha_compra = order.get("fecha_compra", "N/A")

    lines = [
        f"Hola {cliente}, revisé tu pedido **{order['id_pedido']}**.",
        f"Estado actual: **{estado}** (logistica: {estado_envio.replace('_', ' ')}).",
        f"Producto: categoria **{categoria}**. Compra registrada el **{fecha_compra}** "
        f"({dias} dias transcurridos).",
        f"Seguimiento: {tracking}",
    ]

    if order.get("retrasado"):
        lines.append(
            "Hay un retraso reportado. Como compensacion tienes un cupon del 5% "
            "en tu proxima compra."
        )
    else:
        lines.append("No hay retraso reportado en este momento.")

    lines.append(
        "Si necesitas algo mas sobre este pedido, cuentame en que puedo ayudarte."
    )

    return " ".join(lines)


def count_orders_by_state() -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for order in load_orders():
        key = str(order.get("estado_envio", "desconocido"))
        counts[key] = counts.get(key, 0) + 1
    return counts
