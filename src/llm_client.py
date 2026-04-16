import os

import google.generativeai as genai


# Orden sugerido para cuentas tipo Google AI Studio (free tier): Flash primero, luego alternativas.
# Los nombres exactos pueden variar por cuenta/region; si uno da 404, se prueba el siguiente.
DEFAULT_FALLBACK_MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-latest",
    "gemini-2.0-flash",
    "gemini-1.5-pro",
    "gemini-1.5-pro-latest",
]


def _is_not_found_error(error: Exception) -> bool:
    message = str(error).lower()
    return "404" in message or "not found" in message


def get_candidate_models() -> list[str]:
    configured = os.getenv("GEMINI_MODEL", "").strip()
    candidates = []
    if configured:
        candidates.append(configured)
    candidates.extend(DEFAULT_FALLBACK_MODELS)
    return list(dict.fromkeys([model for model in candidates if model]))


def get_gemini_model(model_name: str) -> genai.GenerativeModel:
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "No se encontro GOOGLE_API_KEY. Crea un archivo .env basado en .env.example."
        )

    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name=model_name)


def generate_response(prompt: str, temperature: float = 0.2) -> str:
    last_error = None

    for model_name in get_candidate_models():
        try:
            model = get_gemini_model(model_name)
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                },
            )
            text = (response.text or "").strip()
            if text:
                return text
            return "No se genero contenido de respuesta. Intenta nuevamente."
        except Exception as error:
            last_error = error
            if _is_not_found_error(error):
                # If model is unavailable for this API key/project, try next model.
                continue
            raise

    raise RuntimeError(
        "No fue posible usar ninguno de los modelos configurados. "
        "Deja GEMINI_MODEL vacio en .env para usar el orden por defecto (Flash / free tier), "
        "o copia el ID exacto del modelo desde Google AI Studio (selector de modelo)."
    ) from last_error
