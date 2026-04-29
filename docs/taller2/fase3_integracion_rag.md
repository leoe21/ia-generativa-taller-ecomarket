# Fase 3 - Integracion y ejecucion del codigo

## Resumen de la integracion

El proyecto evoluciona desde el Taller 1, que resolvia dos flujos guiados, hacia un **asistente general con RAG real**.

La implementacion usa:

- `LangChain` para orquestar documentos, chunking y recuperacion.
- `HuggingFaceEmbeddings` para generar vectores.
- `ChromaDB` para almacenar e indexar los embeddings.
- `Ollama`, `Gemini` o `Hugging Face` como motores de generacion.
- `Streamlit` como interfaz de demostracion.

## Archivos clave

- `app.py`: interfaz principal con la nueva pestana **Asistente general RAG**.
- `src/rag_engine.py`: carga documental, chunking, embeddings, Chroma y recuperacion.
- `src/hf_client.py`: cliente para generacion via Hugging Face Inference API.
- `prompts/general_rag_prompt.md`: prompt principal para consultas abiertas.
- `rag_ejemplo.py`: script CLI para probar el flujo RAG sin la interfaz web.
- `knowledge/`: base de conocimiento.

## Mejora del prompt general

El prompt de `prompts/general_rag_prompt.md` fue fortalecido para que no se limite a pedir una respuesta "correcta", sino que opere como una politica de generacion controlada por evidencia.

La version mejorada define:

- un **objetivo principal**: responder con precision, utilidad inmediata y trazabilidad;
- un orden de **prioridades**: exactitud sobre fluidez, utilidad sobre extension, transparencia cuando falte informacion;
- reglas de **sintesis de evidencia**: priorizar fragmentos mas relevantes y evitar mezclar datos incompatibles;
- manejo de **incertidumbre parcial**: separar lo que si puede confirmarse de lo que no;
- adaptacion por **tipo de consulta**: producto, politica, envio, pagos o fuera de alcance;
- y un **formato de salida esperado** para hacer la respuesta mas consistente.

Con esto, el prompt deja de ser una instruccion general y se convierte en una especificacion operativa del comportamiento esperado del LLM dentro del flujo RAG.

## Flujo del sistema

1. El usuario formula una pregunta libre.
2. El sistema carga o reconstruye el indice vectorial.
3. Se recuperan los `top-k` fragmentos mas relevantes desde `ChromaDB`.
4. Si la relevancia es suficiente, se construye el prompt con esos fragmentos y se le indica al modelo como priorizar y sintetizar la evidencia.
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
- `HF_TOKEN=<token de Hugging Face>`
- `HF_MODEL=Qwen/Qwen2.5-7B-Instruct`

### Ejecutar la app

```text
streamlit run app.py
```

### Ejecutar el ejemplo CLI

```text
python rag_ejemplo.py --query "Que metodos de pago aceptan?" --provider ollama
```

Tambien puedes probar con Hugging Face:

```text
python rag_ejemplo.py --query "Cuanto cuesta el cafe organico 500g?" --provider hf
```

## Limitaciones y suposiciones

- La base documental es pequena y simulada con fines academicos.
- El embedding corre en CPU para priorizar compatibilidad local.
- `ChromaDB` local es suficiente para demo, pero no representa la escala de produccion.
- Si no hay evidencia suficiente, el sistema responde con abstencion en lugar de improvisar.
- Los tabs de pedido y devoluciones se conservaron como legado del Taller 1 para comparar la evolucion del proyecto.
- Los proveedores cloud como Gemini y Hugging Face dependen de token, cuota y disponibilidad del servicio externo.
- Aunque el prompt general fue fortalecido, la calidad final sigue dependiendo de la relevancia de los fragmentos recuperados y de la consistencia de la base documental.
