# EcoMarket - Proyecto final (agente + RAG)

Implementacion de un **asistente con agente**, **router de intenciones** y **sistema RAG** para atencion al cliente en e-commerce. El proyecto extiende los Talleres 1 y 2 y agrega:

- embeddings multilingues,
- base vectorial con `ChromaDB`,
- base documental en `knowledge/`,
- recuperacion semantica para consultas abiertas,
- workflow de devoluciones con herramientas LangChain (`verificar_elegibilidad_producto`, `generar_etiqueta_devolucion`),
- chat unificado con router (conocimiento / devolucion / pedido),
- y interfaz Streamlit para demo y sustentacion.

## Estructura principal

| Componente | Descripcion |
|-----------|-------------|
| `app.py` | Interfaz Streamlit: chat unificado con agente + tabs de diagnostico legacy |
| `src/unified_assistant.py` | Router + orquestacion RAG / devoluciones / pedidos |
| `src/agent_tools.py` | Herramientas LangChain del agente de devoluciones |
| `src/intent_router.py` | Clasificacion de rutas y extraccion de datos del mensaje |
| `src/returns_workflow.py` | Workflow explicito verificar -> generar etiqueta |
| `src/rag_engine.py` | Carga documental, chunking, embeddings, Chroma y recuperacion |
| `rag_ejemplo.py` | Script CLI para probar el flujo RAG |
| `knowledge/` | Base de conocimiento con documentos `.md`, `.json` y `.csv` |
| `prompts/general_rag_prompt.md` | Prompt principal para consultas abiertas con control de evidencia, abstencion y formato de salida |
| `docs/taller2/fase1_componentes_rag.md` | Fase 1: seleccion y justificacion de componentes |
| `docs/taller2/fase2_base_conocimiento.md` | Fase 2: documentos, chunking e indexacion |
| `docs/taller2/fase3_integracion_rag.md` | Fase 3: integracion, ejecucion y limitaciones |
| `docs/proyecto_final/fase1_arquitectura_agente.md` | Proyecto final Fase 1: arquitectura y tools |
| `docs/proyecto_final/fase2_implementacion_agente.md` | Proyecto final Fase 2: implementacion |
| `docs/proyecto_final/fase3_analisis_critico.md` | Proyecto final Fase 3: etica y monitoreo |
| `docs/proyecto_final/fase4_despliegue.md` | Proyecto final Fase 4: Streamlit y demo |

## Componentes elegidos

- **Embedding model:** `intfloat/multilingual-e5-base`
- **Vector store:** `ChromaDB`
- **Framework principal:** `LangChain`
- **Generacion:** `Ollama`, `Gemini` o `Hugging Face`

## Guia paso a paso (primera vez)

Sigue estos pasos **en orden**. La demo recomendada del proyecto final usa **Ollama** (local, sin cuota de API).

### Paso 1: Instalar Ollama (si aun no lo tienes)

1. Descarga e instala Ollama desde [https://ollama.com/download](https://ollama.com/download).
2. Abre la aplicacion **Ollama** en Windows (debe quedar en la bandeja del sistema).
3. Comprueba que el servicio responde (PowerShell):

```powershell
curl http://127.0.0.1:11434/api/tags
```

Si ves JSON (aunque sea una lista vacia), el servicio esta activo.

### Paso 2: Descargar el modelo en Ollama

El proyecto usa por defecto **`llama3.2:3b`**. Descargalo una sola vez:

```powershell
ollama pull llama3.2:3b
```

Verifica que aparece en la lista:

```powershell
ollama list
```

### Paso 3: Clonar o abrir el proyecto

Ubicate en la carpeta del repositorio, por ejemplo:

```powershell
cd "ruta\a\Solución Integral IA Generativa - EcoMarket v2"
```

### Paso 4: Crear el entorno virtual de Python

```powershell
python -m venv .venv
```

(Solo hace falta la primera vez.)

### Paso 5: Activar el entorno virtual

**Windows (PowerShell):**

```powershell
.venv\Scripts\Activate.ps1
```

Deberias ver `(.venv)` al inicio de la linea de comandos.

**Windows (CMD):**

```text
.venv\Scripts\activate.bat
```

### Paso 6: Instalar dependencias del proyecto

Con el entorno activado:

```powershell
pip install -r requirements.txt
```

La primera ejecucion puede tardar varios minutos (descarga de librerias y del modelo de embeddings).

### Paso 7: Configurar variables de entorno (opcional pero recomendado)

```powershell
copy .env.example .env
```

Valores utiles en `.env` (Ollama ya viene por defecto en el ejemplo):

```text
OLLAMA_MODEL=llama3.2:3b
EMBEDDING_MODEL=intfloat/multilingual-e5-base
CHROMA_PERSIST_DIR=chroma_db
RAG_TOP_K=4
RAG_MIN_RELEVANCE=0.2
```

`GOOGLE_API_KEY` solo si usaras **Gemini**. `HF_TOKEN` solo si usaras **Hugging Face**.

### Paso 8: Ejecutar la aplicacion

Con el entorno activado y Ollama abierto:

```powershell
streamlit run app.py
```

Se abrira el navegador. En el menu lateral izquierdo veras **dos vistas**:

| Vista | Para que sirve |
|-------|----------------|
| **Atencion al cliente** | Experiencia orientada al usuario final (chat sin metadatos tecnicos). |
| **Sustentacion academica** | Chat con tema detectado, detalles tecnicos, panel de diagnostico y selector de LLM. |

En **Sustentacion academica**, elige **Ollama** en la barra lateral y usa la pestana **Inicio** para probar el agente completo.

### Dos paginas en la app

- `views/cliente.py` — chat sin metadatos tecnicos; Ollama por defecto; errores amigables.
- `views/sustentacion.py` — chat con **Tema detectado**, **Detalles tecnicos**, pestanas **Como usar** y **Panel tecnico**.
- `src/streamlit_ui.py` — logica compartida (router, RAG, devoluciones).

### Resumen rapido (cuando ya configuraste todo)

Cada vez que vuelvas a trabajar en el proyecto:

```powershell
cd "ruta\a\Solución Integral IA Generativa - EcoMarket v2"
.venv\Scripts\Activate.ps1
# Asegurate de que Ollama este abierto en Windows
streamlit run app.py
```

### Si algo falla con Ollama

| Problema | Que revisar |
|----------|-------------|
| Error de conexion a `127.0.0.1:11434` | Abrir la app Ollama; probar `curl http://127.0.0.1:11434/api/tags` |
| Modelo no encontrado | `ollama pull llama3.2:3b` y mismo nombre en `OLLAMA_MODEL` del `.env` |
| Respuestas muy lentas | Normal la primera vez (carga de embeddings); espera o usa un PC con mas RAM |

### APIs opcionales (Gemini / Hugging Face)

No son necesarias para la sustentacion si usas Ollama.

**Hugging Face:** crea un token con permiso de inferencia y agrega en `.env`:

```text
HF_TOKEN=tu_token
HF_MODEL=Qwen/Qwen2.5-7B-Instruct
```

**Gemini:** agrega `GOOGLE_API_KEY` en `.env`. Si aparece error 429, cambia a Ollama en la barra lateral.

## Ejecucion adicional

### Script CLI (solo RAG, sin chat del agente)

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

## Documentacion del proyecto final

Entregables en `docs/proyecto_final/`:

- `fase1_arquitectura_agente.md` — diseno del agente, tools y router
- `fase2_implementacion_agente.md` — implementacion e integracion con el Taller 2
- `fase3_analisis_critico.md` — etica, monitoreo y mejoras
- `fase4_despliegue.md` — interfaz Streamlit y guion de sustentacion

## Asistente unificado (Proyecto final)

1. El usuario escribe en el chat (vista **Atencion al cliente** o pestana **Inicio** en **Sustentacion academica**).
2. El **router** clasifica: `CONOCIMIENTO`, `DEVOLUCION` o `PEDIDO` (tolera errores como *devovler*).
3. Ruta conocimiento: RAG (Chroma) + LLM con evidencia.
4. Ruta devolucion/reclamo: consulta pedido (si hay ID) -> verificar elegibilidad -> etiqueta **o** ticket de reembolso segun estado del envio.
5. Ruta pedido: contexto de `data/orders.json` (~100 pedidos sinteticos) + prompt de estado.

Regenerar pedidos sinteticos:

```text
python scripts/generate_synthetic_orders.py
```

## Notas academicas

- La base documental es simulada pero representa fuentes operativas reales del negocio.
- Los tabs legacy permiten comparar con Talleres 1 y 2.
- Documentacion del proyecto final en `docs/proyecto_final/`.
