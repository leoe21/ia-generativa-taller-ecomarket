import json
from pathlib import Path
from typing import Any, Dict, Optional


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROMPTS_DIR = BASE_DIR / "prompts"


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8") as file:
        return file.read()


def load_orders() -> list[Dict[str, Any]]:
    return _read_json(DATA_DIR / "orders.json")


def load_policies() -> Dict[str, Any]:
    return _read_json(DATA_DIR / "return_policies.json")


def find_order(tracking_number: str) -> Optional[Dict[str, Any]]:
    orders = load_orders()
    normalized = tracking_number.strip()
    for order in orders:
        if order.get("id_pedido") == normalized:
            return order
    return None


def build_order_context(order: Optional[Dict[str, Any]]) -> str:
    if order is None:
        return (
            "RESULTADO_BUSQUEDA: sin_coincidencia\n"
            "OBSERVACION: No se encontro informacion para ese numero de pedido."
        )
    return (
        "RESULTADO_BUSQUEDA: encontrado\n"
        f"ID_PEDIDO: {order['id_pedido']}\n"
        f"CLIENTE: {order['cliente']}\n"
        f"ESTADO_ACTUAL: {order['estado']}\n"
        f"FECHA_ENTREGA_ESTIMADA: {order['fecha_entrega_estimada']}\n"
        f"URL_TRACKING: {order['tracking_url']}\n"
        f"RETRASADO: {order['retrasado']}"
    )


def classify_return(category: str, days_since_purchase: int) -> Dict[str, Any]:
    policies = load_policies()
    category_clean = category.strip().lower()

    if category_clean in policies["no_elegibles"]["categorias"]:
        return {
            "elegible": False,
            "motivo": policies["no_elegibles"]["motivo"],
            "instrucciones": [],
        }

    if category_clean in policies["elegibles"]["categorias"]:
        within_window = days_since_purchase <= int(policies["elegibles"]["ventana_dias"])
        if within_window:
            return {
                "elegible": True,
                "motivo": "La devolucion cumple la politica vigente.",
                "instrucciones": policies["elegibles"]["instrucciones"],
            }
        return {
            "elegible": False,
            "motivo": "La solicitud excede la ventana maxima de 30 dias.",
            "instrucciones": [],
        }

    return {
        "elegible": False,
        "motivo": "Categoria no reconocida. Revisa si es perecederos, higiene, ropa o accesorios.",
        "instrucciones": [],
    }


def load_order_prompt() -> str:
    return _read_text(PROMPTS_DIR / "order_status_prompt.md")


def load_returns_prompt() -> str:
    return _read_text(PROMPTS_DIR / "returns_prompt.md")
