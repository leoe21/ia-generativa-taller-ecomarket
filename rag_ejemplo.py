import argparse

from src.llm_client import generate_response
from src.open_source_client import generate_response_ollama
from src.rag_engine import (
    build_general_rag_prompt,
    format_retrieved_context,
    get_vector_store,
    has_sufficient_context,
    retrieve_knowledge,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejemplo CLI del sistema RAG de EcoMarket.")
    parser.add_argument("--query", required=True, help="Pregunta del cliente.")
    parser.add_argument(
        "--provider",
        default="ollama",
        choices=["ollama", "gemini"],
        help="Motor de generacion a usar.",
    )
    parser.add_argument(
        "--top-k",
        default=4,
        type=int,
        help="Numero de fragmentos a recuperar.",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Reconstruye el indice vectorial antes de consultar.",
    )
    args = parser.parse_args()

    vector_store = get_vector_store(force_rebuild=args.rebuild)
    retrieval_results = retrieve_knowledge(args.query, vector_store=vector_store, k=args.top_k)
    retrieved_context = format_retrieved_context(retrieval_results)

    print("\n=== CONTEXTO RECUPERADO ===\n")
    print(retrieved_context)

    if not has_sufficient_context(retrieval_results):
        print("\n=== RESPUESTA ===\n")
        print(
            "No cuento con suficiente informacion en la base de conocimiento de EcoMarket "
            "para responder esta solicitud con confianza."
        )
        return

    prompt = build_general_rag_prompt(args.query, retrieved_context)
    if args.provider == "ollama":
        answer = generate_response_ollama(prompt, temperature=0.1)
    else:
        answer = generate_response(prompt, temperature=0.1)

    print("\n=== RESPUESTA ===\n")
    print(answer)


if __name__ == "__main__":
    main()
