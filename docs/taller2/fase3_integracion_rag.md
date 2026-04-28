# Fase 3 - Integracion y ejecucion del codigo

## Resumen de la integracion

El proyecto evoluciona desde el Taller 1, que resolvia dos flujos guiados, hacia un **asistente general con RAG real**.

La implementacion usa:

- `LangChain` para orquestar documentos, chunking y recuperacion.
- `HuggingFaceEmbeddings` para generar vectores.
- `ChromaDB` para almacenar e indexar los embeddings.
- `Ollama` o `Gemini` como motores de generacion.
- `Streamlit` como interfaz de demostracion.

## Archivos clave

- `app.py`: interfaz principal con la nueva pestana **Asistente general RAG**.
- `src/rag_engine.py`: carga documental, chunking, embeddings, Chroma y recuperacion.
- `prompts/general_rag_prompt.md`: prompt principal para consultas abiertas.
- `rag_ejemplo.py`: script CLI para probar el flujo RAG sin la interfaz web.
- `knowledge/`: base de conocimiento.

## Flujo del sistema

1. El usuario formula una pregunta libre.
2. El sistema carga o reconstruye el indice vectorial.
3. Se recuperan los `top-k` fragmentos mas relevantes desde `ChromaDB`.
4. Si la relevancia es suficiente, se construye el prompt con esos fragmentos.
5. El LLM responde solo con base en el contexto recuperado.
6. Si la evidencia no es suficiente, el sistema se abstiene y recomienda escalar a soporte humano.

## Ejecucion

### Requisitos

- Python 3.10+
- Ollama en ejecucion si se usa el modo local
- Dependencias instaladas desde `requirements.txt`

### Instalacion

```text
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Variables de entorno

Configurar `.env` a partir de `.env.example`.

Variables principales:

- `EMBEDDING_MODEL=intfloat/multilingual-e5-base`
- `CHROMA_PERSIST_DIR=chroma_db`
- `RAG_TOP_K=4`
- `RAG_CHUNK_SIZE=700`
- `RAG_CHUNK_OVERLAP=120`
- `RAG_MIN_RELEVANCE=0.2`

### Ejecutar la app

```text
streamlit run app.py
```

### Ejecutar el ejemplo CLI

```text
python rag_ejemplo.py --query "Que metodos de pago aceptan?" --provider ollama
```

## Limitaciones y suposiciones

- La base documental es pequena y simulada con fines academicos.
- El embedding corre en CPU para priorizar compatibilidad local.
- `ChromaDB` local es suficiente para demo, pero no representa la escala de produccion.
- Si no hay evidencia suficiente, el sistema responde con abstencion en lugar de improvisar.
- Los tabs de pedido y devoluciones se conservaron como legado del Taller 1 para comparar la evolucion del proyecto.
