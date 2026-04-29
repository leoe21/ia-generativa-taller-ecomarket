import os

from huggingface_hub import InferenceClient


DEFAULT_HF_MODEL = "Qwen/Qwen2.5-7B-Instruct"


def get_hf_token() -> str:
    token = os.getenv("HF_TOKEN", "").strip()
    if not token:
        raise ValueError(
            "No se encontro HF_TOKEN. Crea un archivo .env basado en .env.example."
        )
    return token


def get_hf_model() -> str:
    return os.getenv("HF_MODEL", DEFAULT_HF_MODEL).strip() or DEFAULT_HF_MODEL


def generate_response_hf(prompt: str, temperature: float = 0.2) -> str:
    client = InferenceClient(provider="hf-inference", api_key=get_hf_token())
    response = client.text_generation(
        prompt=prompt,
        model=get_hf_model(),
        max_new_tokens=300,
        temperature=temperature,
        return_full_text=False,
    )
    text = (response or "").strip()
    if not text:
        return "No se genero contenido de respuesta desde Hugging Face. Intenta nuevamente."
    return text
