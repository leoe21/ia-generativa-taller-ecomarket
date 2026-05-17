"""Genera data/orders.json con 100 pedidos sinteticos para demos de reclamos."""

from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "orders.json"

NAMES = [
    "Ana Lopez",
    "Carlos Perez",
    "Maria Gomez",
    "Luis Torres",
    "Sofia Rojas",
    "Jorge Diaz",
    "Valeria Ruiz",
    "Diego Martinez",
    "Laura Herrera",
    "Andres Molina",
    "Camila Vargas",
    "Nicolas Soto",
    "Paula Castro",
    "Felipe Rios",
    "Daniela Mora",
]

CATEGORIES = ["perecederos", "higiene", "ropa", "accesorios"]

STATE_PROFILES = [
    {
        "estado_envio": "confirmado_compra",
        "estado": "Compra confirmada",
        "permite_devolucion_fisica": False,
        "permite_reclamo_reembolso": True,
    },
    {
        "estado_envio": "procesando",
        "estado": "Procesando",
        "permite_devolucion_fisica": False,
        "permite_reclamo_reembolso": True,
    },
    {
        "estado_envio": "en_transito",
        "estado": "En camino",
        "permite_devolucion_fisica": False,
        "permite_reclamo_reembolso": True,
    },
    {
        "estado_envio": "entregado",
        "estado": "Entregado",
        "permite_devolucion_fisica": True,
        "permite_reclamo_reembolso": True,
    },
]


def build_orders(total: int = 100) -> list[dict]:
    random.seed(42)
    orders: list[dict] = []
    per_state = total // len(STATE_PROFILES)

    for index in range(total):
        profile = STATE_PROFILES[index % len(STATE_PROFILES)]
        order_id = str(10001 + index)
        category = random.choice(CATEGORIES)
        if profile["estado_envio"] == "entregado":
            days = random.randint(1, 40)
        else:
            days = random.randint(0, 10)

        retrasado = profile["estado_envio"] == "en_transito" and index % 7 == 0
        orders.append(
            {
                "id_pedido": order_id,
                "cliente": random.choice(NAMES),
                "estado_envio": profile["estado_envio"],
                "estado": profile["estado"],
                "categoria_producto": category,
                "dias_desde_compra": days,
                "fecha_compra": f"2026-04-{max(1, 28 - days):02d}",
                "monto_cop": random.randint(15000, 120000),
                "tracking_url": f"https://tracking.ecomarket.co/{order_id}",
                "retrasado": retrasado,
                "permite_devolucion_fisica": profile["permite_devolucion_fisica"],
                "permite_reclamo_reembolso": profile["permite_reclamo_reembolso"],
            }
        )

    # Pedidos fijos utiles para la demo oral
    demo_overrides = {
        "12345": {
            "id_pedido": "12345",
            "cliente": "Ana Lopez",
            "estado_envio": "en_transito",
            "estado": "En camino",
            "categoria_producto": "ropa",
            "dias_desde_compra": 3,
            "fecha_compra": "2026-05-14",
            "monto_cop": 45900,
            "tracking_url": "https://tracking.ecomarket.co/12345",
            "retrasado": False,
            "permite_devolucion_fisica": False,
            "permite_reclamo_reembolso": True,
        },
        "54321": {
            "id_pedido": "54321",
            "cliente": "Carlos Perez",
            "estado_envio": "entregado",
            "estado": "Entregado",
            "categoria_producto": "ropa",
            "dias_desde_compra": 8,
            "fecha_compra": "2026-05-09",
            "monto_cop": 52000,
            "tracking_url": "https://tracking.ecomarket.co/54321",
            "retrasado": False,
            "permite_devolucion_fisica": True,
            "permite_reclamo_reembolso": True,
        },
    }
    by_id = {order["id_pedido"]: order for order in orders}
    by_id.update(demo_overrides)
    return sorted(by_id.values(), key=lambda item: int(item["id_pedido"]))


def main() -> None:
    orders = build_orders(100)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as file:
        json.dump(orders, file, ensure_ascii=False, indent=2)
    print(f"Generados {len(orders)} pedidos en {OUTPUT}")


if __name__ == "__main__":
    main()
