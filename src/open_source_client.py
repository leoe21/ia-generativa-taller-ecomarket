import json
import os
from urllib import error, request


def get_ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "llama3.2:3b").strip() or "llama3.2:3b"


def get_ollama_base_url() -> str:
    base = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").strip().rstrip("/")
    return base or "http://127.0.0.1:11434"


def generate_response_ollama(prompt: str, temperature: float = 0.2) -> str:
    payload = {
        "model": get_ollama_model(),
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }
    body = json.dumps(payload).encode("utf-8")
    base = get_ollama_base_url()
    url = f"{base}/api/generate"
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
            text = (data.get("response") or "").strip()
            if not text:
                return "No se genero contenido desde Ollama. Intenta nuevamente."
            return text
    except error.URLError as exc:
        raise RuntimeError(
            f"No fue posible conectar con Ollama en {base}. "
            "Comprueba: (1) Ollama instalado desde https://ollama.com/download , "
            "(2) abre la app Ollama en Windows (debe aparecer en la bandeja), "
            f"(3) en PowerShell: `ollama list` y `curl {base}/api/tags`. "
            "Si usas otro puerto, define OLLAMA_BASE_URL en .env."
        ) from exc
