"""Router de intenciones para el asistente unificado (opcion A)."""

from __future__ import annotations

import re
import unicodedata
from enum import Enum


class AssistantRoute(str, Enum):
    KNOWLEDGE = "CONOCIMIENTO"
    RETURNS = "DEVOLUCION"
    ORDER_STATUS = "PEDIDO"


# Subcadenas tolerantes a errores de teclado
_RETURN_STEMS = (
    "devolv",
    "devov",
    "devoc",  # devocluion, devocion
    "devulc",
    "deboluc",
    "devuelt",
    "reembols",
    "reembolz",
    "reclam",
    "cancel",
    "devolverlo",
    "devovler",
    "devolvero",
    "quiero devolver",
    "solicito devolucion",
    "hacer una dev",
    "etiqueta de devolucion",
    "generar etiqueta",
    "devolucion",
    "devoluc",
    "cambio de producto",
)

_DAMAGE_OR_DEFECT_STEMS = (
    "danad",
    "danado",
    "defectu",
    "defecto",
    "roto",
    "averiad",
    "mal estado",
    "llego mal",
    "salio mal",
    "mes aio",  # typo frecuente de "me salio"
    "no sirve",
    "no funciona",
    "estrope",
)

# Palabras objetivo para coincidencia aproximada (distancia <= 2)
_FUZZY_RETURN_WORDS = (
    "devolucion",
    "devolver",
    "devoluciones",
    "reembolso",
    "reclamacion",
    "cancelacion",
)

_ORDER_KEYWORDS = (
    "estado del pedido",
    "estado de mi pedido",
    "numero de pedido",
    "numero pedido",
    "seguimiento",
    "tracking",
    "donde esta mi pedido",
    "rastrear pedido",
    "en transito",
    "en camino",
    "compra confirmada",
    "dudas sobre mi pedido",
    "duda sobre mi pedido",
    "pregunta sobre mi pedido",
    "ayuda con mi pedido",
    "tengo dudas sobre mi pedido",
)

# "mi pedido" solo cuenta como consulta de estado si NO hay devolucion/reclamo
_ORDER_ONLY_PHRASES = _ORDER_KEYWORDS + (
    "mi orden",
    "sobre mi orden",
)

_CATEGORY_ALIASES: dict[str, tuple[str, ...]] = {
    "perecederos": ("perecedero", "perecederos", "comida", "cafe", "granola", "alimento"),
    "higiene": ("higiene", "shampoo", "jabon", "cosmetico", "aseo personal"),
    "ropa": ("ropa", "camiseta", "prenda", "vestido", "pantalon"),
    "accesorios": ("accesorio", "accesorios", "botella", "cubiertos", "termo"),
}


def _normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn").lower()


def _levenshtein_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous = list(range(len(right) + 1))
    for index, char_left in enumerate(left, start=1):
        current = [index]
        for j, char_right in enumerate(right, start=1):
            insert_cost = current[j - 1] + 1
            delete_cost = previous[j] + 1
            replace_cost = previous[j - 1] + (char_left != char_right)
            current.append(min(insert_cost, delete_cost, replace_cost))
        previous = current
    return previous[-1]


def _fuzzy_return_word_match(text: str) -> bool:
    tokens = re.findall(r"[a-z]{5,}", text)
    for token in tokens:
        for keyword in _FUZZY_RETURN_WORDS:
            if abs(len(token) - len(keyword)) > 3:
                continue
            if _levenshtein_distance(token, keyword) <= 2:
                return True
    return False


def _has_return_intent(text: str) -> bool:
    if any(stem in text for stem in _RETURN_STEMS):
        return True
    if any(stem in text for stem in _DAMAGE_OR_DEFECT_STEMS):
        return True
    if _fuzzy_return_word_match(text):
        return True
    return False


def _has_order_intent(text: str) -> bool:
    if any(keyword in text for keyword in _ORDER_ONLY_PHRASES):
        return True
    if re.search(r"\b(pedido|orden)\b", text) and not _has_return_intent(text):
        return True
    return False


def classify_route(message: str) -> AssistantRoute:
    text = _normalize_text(message.strip())
    if not text:
        return AssistantRoute.KNOWLEDGE

    order_id = _extract_order_id(text)
    return_intent = _has_return_intent(text)

    # Devolucion/reclamo tiene prioridad aunque diga "mi pedido"
    if return_intent:
        return AssistantRoute.RETURNS

    if order_id or _has_order_intent(text):
        return AssistantRoute.ORDER_STATUS

    return AssistantRoute.KNOWLEDGE


def _extract_order_id(text: str) -> str | None:
    patterns = (
        r"(?:pedido|orden|order)\s*(?:n[o°]?\.?|numero|#)?\s*[:#]?\s*(\d{4,8})",
        r"(?:pedido|orden)\s+(\d{4,8})",
        r"\b(\d{5})\b",
        r"\b(1\d{4})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def extract_return_slots(message: str) -> dict[str, int | str | None]:
    text = _normalize_text(message.strip())
    category: str | None = None
    for canonical, aliases in _CATEGORY_ALIASES.items():
        if any(alias in text for alias in aliases):
            category = canonical
            break

    days: int | None = None
    day_patterns = (
        r"(\d{1,3})\s*dias?",
        r"hace\s*(\d{1,3})",
        r"(\d{1,3})\s*dias?\s*desde",
    )
    for pattern in day_patterns:
        match = re.search(pattern, text)
        if match:
            days = int(match.group(1))
            break

    order_id = _extract_order_id(text)
    return {
        "categoria": category,
        "dias_desde_compra": days,
        "id_pedido": order_id,
    }


def extract_order_id(message: str) -> str | None:
    return _extract_order_id(_normalize_text(message.strip()))
