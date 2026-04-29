# EcoMarket - Taller practico #2

Implementacion de un **sistema RAG** para optimizar la atencion al cliente en una empresa de e-commerce. El proyecto extiende el trabajo del Taller 1 y agrega:

- embeddings multilingues,
- base vectorial con `ChromaDB`,
- base documental en `knowledge/`,
- recuperacion semantica para consultas abiertas,
- y una nueva interfaz en Streamlit para responder con evidencia o abstenerse si no hay contexto suficiente.

## Estructura principal

| Componente | Descripcion |
|-----------|-------------|
| `app.py` | Interfaz Streamlit con asistente general RAG y tabs legacy del Taller 1 |
| `src/rag_engine.py` | Carga documental, chunking, embeddings, Chroma y recuperacion |
| `rag_ejemplo.py` | Script CLI para probar el flujo RAG |
| `knowledge/` | Base de conocimiento con documentos `.md`, `.json` y `.csv` |
| `prompts/general_rag_prompt.md` | Prompt principal para consultas abiertas |
| `docs/taller2/fase1_componentes_rag.md` | Fase 1: seleccion y justificacion de componentes |
| `docs/taller2/fase2_base_conocimiento.md` | Fase 2: documentos, chunking e indexacion |
| `docs/taller2/fase3_integracion_rag.md` | Fase 3: integracion, ejecucion y limitaciones |

## Componentes elegidos

- **Embedding model:** `intfloat/multilingual-e5-base`
- **Vector store:** `ChromaDB`
- **Framework principal:** `LangChain`
- **Generacion:** `Ollama`, `Gemini` o `Hugging Face`

## Instalacion

### 1. Crear entorno virtual

```text
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

Copia `.env.example` a `.env`.

Variables principales:

```text
OLLAMA_MODEL=llama3.2:3b
EMBEDDING_MODEL=intfloat/multilingual-e5-base
CHROMA_PERSIST_DIR=chroma_db
RAG_TOP_K=4
RAG_CHUNK_SIZE=700
RAG_CHUNK_OVERLAP=120
RAG_MIN_RELEVANCE=0.2
```

`GOOGLE_API_KEY` solo es necesaria si vas a usar Gemini.
`HF_TOKEN` solo es necesario si vas a usar Hugging Face.

### 3. Preparar Ollama

1. Instala Ollama: [https://ollama.com/download](https://ollama.com/download)
2. Deja el servicio activo en `http://127.0.0.1:11434`
3. Descarga un modelo local:

```text
ollama pull llama3.2:3b
```

### 4. Preparar Hugging Face (opcional)

1. Crea un token en Hugging Face con permiso `Inference -> Make calls to Inference Providers`
2. Agrega en `.env`:

```text
HF_TOKEN=tu_token
HF_MODEL=Qwen/Qwen2.5-7B-Instruct
```

## Ejecucion

### App web

```text
streamlit run app.py
```

### Script CLI

```text
python rag_ejemplo.py --query "Que metodos de pago aceptan?" --provider ollama
```

Opciones utiles:

```text
python rag_ejemplo.py --query "Puedo devolver un shampoo?" --provider ollama --rebuild
python rag_ejemplo.py --query "Tienen disponible la botella reutilizable?" --provider gemini --top-k 5
python rag_ejemplo.py --query "Cuanto cuesta el cafe organico 500g?" --provider hf
```

## Como funciona el RAG

1. Los documentos en `knowledge/` se cargan y convierten en objetos `Document`.
2. Se fragmentan con `RecursiveCharacterTextSplitter`.
3. Cada fragmento se transforma en embedding.
4. Los vectores se almacenan en `ChromaDB`.
5. Ante una consulta, se recuperan los fragmentos mas relevantes.
6. El LLM responde solo con ese contexto.
7. Si la relevancia es insuficiente, el asistente indica que no cuenta con herramientas para responder con seguridad.

## Base de conocimiento incluida

- `knowledge/politicas_operativas.md`
- `knowledge/faqs_ecomarket.json`
- `knowledge/catalogo_productos.csv`
- `knowledge/guia_logistica.md`

## Notas academicas

- La base documental es simulada pero representa fuentes operativas reales del negocio.
- El sistema conserva los tabs de pedido y devoluciones como comparativo con el Taller 1.
- La entrega principal del Taller 2 debe apoyarse en los tres archivos de `docs/` creados para esta version.
