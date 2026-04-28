import csv
import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PROMPTS_DIR = BASE_DIR / "prompts"
KNOWLEDGE_DIR = BASE_DIR / "knowledge"


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
        return "No se encontro informacion para ese numero de pedido."
    return (
        f"ID_PEDIDO: {order['id_pedido']} | Estado: {order['estado']} | "
        f"Entrega: {order['fecha_entrega_estimada']} | "
        f"URL_TRACKING: {order['tracking_url']} | "
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


def load_general_rag_prompt() -> str:
    return _read_text(PROMPTS_DIR / "general_rag_prompt.md")


def get_embedding_model_name() -> str:
    return os.getenv("EMBEDDING_MODEL", "intfloat/multilingual-e5-base").strip() or "intfloat/multilingual-e5-base"


def get_chroma_persist_dir() -> Path:
    configured = os.getenv("CHROMA_PERSIST_DIR", "chroma_db").strip() or "chroma_db"
    return (BASE_DIR / configured).resolve()


def get_rag_top_k() -> int:
    return max(1, int(os.getenv("RAG_TOP_K", "4")))


def get_rag_chunk_size() -> int:
    return max(200, int(os.getenv("RAG_CHUNK_SIZE", "700")))


def get_rag_chunk_overlap() -> int:
    return max(0, int(os.getenv("RAG_CHUNK_OVERLAP", "120")))


def get_min_relevance() -> float:
    return float(os.getenv("RAG_MIN_RELEVANCE", "0.2"))


def get_knowledge_files() -> list[Path]:
    supported_extensions = {".md", ".txt", ".json", ".csv"}
    if not KNOWLEDGE_DIR.exists():
        return []
    return sorted(
        [
            path
            for path in KNOWLEDGE_DIR.rglob("*")
            if path.is_file() and path.suffix.lower() in supported_extensions
        ]
    )


def _load_text_document(path: Path) -> list[Document]:
    content = _read_text(path).strip()
    if not content:
        return []
    return [
        Document(
            page_content=content,
            metadata={
                "source": path.name,
                "source_path": str(path.relative_to(BASE_DIR)),
                "doc_type": path.suffix.lower().lstrip("."),
            },
        )
    ]


def _load_json_documents(path: Path) -> list[Document]:
    data = _read_json(path)
    documents: list[Document] = []

    if isinstance(data, list):
        for index, item in enumerate(data, start=1):
            title = f"entrada_{index}"
            if isinstance(item, dict):
                title = (
                    item.get("pregunta")
                    or item.get("titulo")
                    or item.get("categoria")
                    or title
                )
                content = json.dumps(item, ensure_ascii=False, indent=2)
            else:
                content = str(item)
            documents.append(
                Document(
                    page_content=f"Registro: {title}\n{content}",
                    metadata={
                        "source": path.name,
                        "source_path": str(path.relative_to(BASE_DIR)),
                        "doc_type": "json",
                        "record_index": index,
                    },
                )
            )
        return documents

    if isinstance(data, dict):
        for key, value in data.items():
            documents.append(
                Document(
                    page_content=(
                        f"Seccion: {key}\n"
                        f"{json.dumps(value, ensure_ascii=False, indent=2)}"
                    ),
                    metadata={
                        "source": path.name,
                        "source_path": str(path.relative_to(BASE_DIR)),
                        "doc_type": "json",
                        "section": key,
                    },
                )
            )
        return documents

    return [
        Document(
            page_content=str(data),
            metadata={
                "source": path.name,
                "source_path": str(path.relative_to(BASE_DIR)),
                "doc_type": "json",
            },
        )
    ]


def _load_csv_documents(path: Path) -> list[Document]:
    documents: list[Document] = []
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        for index, row in enumerate(reader, start=1):
            content = (
                f"Producto: {row.get('nombre', '')}\n"
                f"SKU: {row.get('sku', '')}\n"
                f"Categoria: {row.get('categoria', '')}\n"
                f"Descripcion: {row.get('descripcion', '')}\n"
                f"Precio en COP: {row.get('precio_cop', '')}\n"
                f"Stock disponible: {row.get('stock', '')}\n"
                f"Disponible para la venta: {row.get('disponible', '')}\n"
                "Usa estos datos para responder preguntas sobre precio, disponibilidad, "
                "stock y caracteristicas del producto."
            )
            documents.append(
                Document(
                    page_content=content,
                    metadata={
                        "source": path.name,
                        "source_path": str(path.relative_to(BASE_DIR)),
                        "doc_type": "csv",
                        "record_index": index,
                    },
                )
            )
    return documents


def load_knowledge_documents() -> list[Document]:
    documents: list[Document] = []
    for path in get_knowledge_files():
        suffix = path.suffix.lower()
        if suffix in {".md", ".txt"}:
            documents.extend(_load_text_document(path))
        elif suffix == ".json":
            documents.extend(_load_json_documents(path))
        elif suffix == ".csv":
            documents.extend(_load_csv_documents(path))
    return documents


def chunk_knowledge_documents(documents: list[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=get_rag_chunk_size(),
        chunk_overlap=get_rag_chunk_overlap(),
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    for index, chunk in enumerate(chunks, start=1):
        chunk.metadata["chunk_id"] = index
    return chunks


def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(
        model_name=get_embedding_model_name(),
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def _vector_store_has_data() -> bool:
    persist_dir = get_chroma_persist_dir()
    return persist_dir.exists() and any(persist_dir.iterdir())


def get_vector_store(force_rebuild: bool = False) -> Chroma:
    persist_dir = get_chroma_persist_dir()
    embeddings = get_embeddings()

    if force_rebuild and persist_dir.exists():
        shutil.rmtree(persist_dir)

    if force_rebuild or not _vector_store_has_data():
        raw_documents = load_knowledge_documents()
        if not raw_documents:
            raise RuntimeError(
                "No se encontraron documentos en la carpeta knowledge/ para construir el indice RAG."
            )
        chunked_documents = chunk_knowledge_documents(raw_documents)
        return Chroma.from_documents(
            documents=chunked_documents,
            embedding=embeddings,
            persist_directory=str(persist_dir),
        )

    return Chroma(
        persist_directory=str(persist_dir),
        embedding_function=embeddings,
    )


def retrieve_knowledge(
    question: str,
    vector_store: Optional[Chroma] = None,
    k: Optional[int] = None,
) -> list[dict[str, Any]]:
    store = vector_store or get_vector_store()
    top_k = k or get_rag_top_k()
    query_text = question.strip()
    if query_text:
        query_text = f"query: {query_text}"

    try:
        results = store.similarity_search_with_relevance_scores(query_text, k=top_k)
        return [{"document": document, "score": score} for document, score in results]
    except Exception:
        documents = store.similarity_search(query_text, k=top_k)
        return [{"document": document, "score": None} for document in documents]


def has_sufficient_context(results: list[dict[str, Any]]) -> bool:
    if not results:
        return False

    scored_results = [item["score"] for item in results if item["score"] is not None]
    if not scored_results:
        return True

    return max(scored_results) >= get_min_relevance()


def format_retrieved_context(results: list[dict[str, Any]]) -> str:
    if not results:
        return "Sin contexto recuperado."

    blocks = []
    for index, item in enumerate(results, start=1):
        document = item["document"]
        score = item["score"]
        source = document.metadata.get("source", "desconocida")
        score_label = "N/A" if score is None else f"{score:.3f}"
        blocks.append(
            f"[Fragmento {index}] Fuente: {source} | Relevancia: {score_label}\n"
            f"{document.page_content.strip()}"
        )
    return "\n\n".join(blocks)


def build_general_rag_prompt(question: str, retrieved_context: str) -> str:
    template = load_general_rag_prompt()
    return template.format(
        question=question.strip(),
        retrieved_context=retrieved_context.strip(),
    )


def get_knowledge_base_summary() -> list[dict[str, Any]]:
    summary = []
    for path in get_knowledge_files():
        summary.append(
            {
                "archivo": path.name,
                "ruta": str(path.relative_to(BASE_DIR)),
                "tipo": path.suffix.lower().lstrip("."),
            }
        )
    return summary
