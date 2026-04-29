# Fase 3 — Ingeniería de prompts y despliegue

Esta fase cumple el requisito del taller: **diseñar prompts efectivos** y **demostrar su impacto en código**, con una cadena clara entre instrucción, contexto recuperado (RAG) y respuesta del modelo. La aplicación está implementada en **Streamlit** (`app.py`).

En la versión mejorada del Taller 1, los prompts ya no usan instrucciones vagas como "genera la mejor respuesta", sino que definen con precisión:

- el **objetivo** de la respuesta,
- los **datos obligatorios** que deben aparecer,
- la **lógica de decisión** por escenario,
- las **restricciones de alucinación**,
- y una **estructura esperada de salida**.

Esto hace que la calidad del resultado no dependa solo de la intuición del modelo, sino de reglas observables y evaluables.

Para el ejercicio académico se prioriza un modelo **open-source local** vía **Ollama** (nota del enunciado). La app también permite **Gemini por API** como opción opcional para comparar.

---

## 3.1 Prompt 1: consulta de estado de pedido

**Archivo:** `prompts/order_status_prompt.md`

**Variables que inyecta el código:** `{order_context}` (texto generado desde `data/orders.json` según el ID buscado) y `{tracking_number}`.

**Diseño mejorado del prompt:**

- Define un **objetivo explícito**: responder con exactitud, utilidad y tono profesional.
- Obliga a usar **solo** el contexto del pedido.
- Distingue dos escenarios operativos:
  - pedido no encontrado,
  - pedido encontrado.
- Si el pedido existe, exige mencionar de forma obligatoria:
  - ID del pedido,
  - estado actual,
  - fecha estimada de entrega,
  - enlace de seguimiento.
- Si el pedido está **retrasado** (`retrasado: true`), obliga a:
  - disculparse,
  - mencionar el cupón del 5%.
- Si el pedido **no** está retrasado, prohíbe mencionar compensaciones.
- Define una **estructura esperada** de 3 o 4 oraciones y un máximo de 120 palabras.

**Por qué esta versión es mejor:** la instrucción ya no delega al modelo la noción ambigua de "mejor respuesta", sino que especifica qué información debe aparecer, cuándo debe aparecer y qué no puede inventarse.

**Criterios del taller cubiertos:** número de seguimiento / ID de pedido, contexto con **al menos 10 pedidos** en la base simulada (`data/orders.json`), tono de agente, reglas de negocio explícitas y criterios de salida verificables.

---

## 3.2 Prompt 2: gestión de devoluciones (clasificación)

**Archivo:** `prompts/returns_prompt.md`

**Variables:** `{policy_context}` (JSON legible de `data/return_policies.json`), `{category}`, `{days_since_purchase}`.

**Diseño mejorado del prompt:**

- Define un **objetivo explícito**: decidir elegibilidad y explicar la decisión.
- Obliga a declarar de manera textual si la solicitud **es elegible o no**.
- Convierte la política en reglas operativas claras:
  - **Perecederos / higiene:** no elegibles por seguridad y control sanitario.
  - **Ropa / accesorios dentro de 30 días:** elegibles.
  - **Ropa / accesorios fuera de 30 días:** no elegibles por exceder la ventana máxima.
- Si la solicitud es elegible, exige resumir los pasos de devolución.
- Si no es elegible, exige explicar el motivo y ofrecer contacto con soporte humano.
- Define una **estructura esperada** de 3 a 5 oraciones y máximo 140 palabras.

La app además ejecuta una **clasificación previa** en `src/rag_engine.py` (`classify_return`) para mostrar en pantalla si el caso es elegible; el modelo redacta la respuesta final según el prompt y el contexto de políticas.

**Por qué esta versión es mejor:** en vez de pedir una respuesta "final" genérica, el prompt especifica la decisión, la justificación y los pasos o alternativa esperados, reduciendo ambigüedad y aumentando consistencia.

---

## 3.3 Cómo se encadena el RAG en el código

1. **Recuperación:** se leen `data/orders.json` y `data/return_policies.json` (simulan inventario/políticas).
2. **Construcción del prompt:** `app.py` carga las plantillas `.md`, rellena variables y envía un **único texto** al generador.
3. **Generación:** según la opción en la barra lateral:
   - **Open-source local (Ollama):** `src/open_source_client.py` → `POST` a `http://localhost:11434/api/generate` con el modelo definido en `OLLAMA_MODEL` (por defecto `llama3.2:3b`).
   - **Gemini API:** `src/llm_client.py` (opcional; requiere `GOOGLE_API_KEY`).
4. **Respaldo:** si Gemini devuelve error de **cuota (429)**, la interfaz puede mostrar una respuesta de respaldo basada en los mismos datos locales (sin depender del LLM en ese momento).

Además, la construcción del contexto fue mejorada para que el prompt reciba campos legibles y semiestructurados en lugar de texto demasiado comprimido. En el caso de pedidos, el contexto ahora indica explícitamente si hubo coincidencia, el estado, la fecha estimada, el tracking y si existe retraso.

---

## 3.4 Qué demuestra la mejora de prompts

La mejora central de esta fase no es solo "dar más instrucciones", sino convertir el prompt en una **especificación operativa**. En concreto:

- Se reemplazaron instrucciones subjetivas por reglas verificables.
- Se separó el **objetivo**, las **restricciones** y la **estructura de salida**.
- Se hizo explícita la diferencia entre escenarios.
- Se redujo el margen para respuestas bonitas pero incompletas.

Esto es importante para evaluación académica porque permite justificar por qué el prompt está diseñado con intención, criterio y control del comportamiento del modelo.

---

## 3.5 Despliegue y ejecución (modelo Ollama requerido para la demo principal)

El taller pide evidenciar prompts con un modelo accesible; **Ollama** es el camino recomendado porque no depende de cuotas de API.

### Requisitos

- **Python 3.10+**
- **Ollama** instalado y en ejecución (servidor local en el puerto **11434**).
- Modelo descargado en Ollama (el proyecto usa por defecto **`llama3.2:3b`**).

### Pasos (Windows, PowerShell)

1. **Instalar Ollama** desde [https://ollama.com/download](https://ollama.com/download) y comprobar que la aplicación esté abierta (el servicio suele quedar escuchando en `localhost:11434`).

2. **Descargar el modelo** (una sola vez; no va dentro del entorno virtual de Python):

   ```text
   ollama pull llama3.2:3b
   ```

   Comprobar con `ollama list` que el modelo aparece listado.

3. **Entorno virtual del proyecto** (solo para dependencias Python):

   ```text
   cd "ruta\al\proyecto\EcoMarket v2"
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

4. **Variables de entorno (opcional):** copiar `.env.example` a `.env` y, si quieres otro modelo de Ollama, ajustar:

   ```text
   OLLAMA_MODEL=llama3.2:3b
   ```

   `GOOGLE_API_KEY` solo es necesario si usas la opción Gemini en la barra lateral. Puedes dejar `GEMINI_MODEL` vacío: la app intentará modelos Flash en orden (compatibles con el free tier típico de Google AI Studio); si prefieres uno fijo, usa el ID que muestre AI Studio en el selector de modelo.

5. **Ejecutar la aplicación:**

   ```text
   streamlit run app.py
   ```

6. En el navegador, en la **barra lateral**, seleccionar **“Open-source local (Ollama)”**.

7. Probar:
   - Pestaña **Estado de pedido:** por ejemplo `12345`, `10002` (retrasado), o un ID inexistente.
   - Pestaña **Gestión de devoluciones:** combinar categoría (perecederos/higiene vs ropa/accesorios) y días desde la compra.

### Si algo falla con Ollama

- Mensaje de conexión: confirmar que Ollama está instalado y que **no** hay firewall bloqueando `localhost:11434`.
- Modelo no encontrado: ejecutar de nuevo `ollama pull` con el mismo nombre que pusiste en `OLLAMA_MODEL`.

---

## 3.6 Evidencia para entrega (repositorio)

Incluir en el repositorio:

- `prompts/order_status_prompt.md` y `prompts/returns_prompt.md`
- `data/orders.json` (≥10 pedidos) y `data/return_policies.json`
- `app.py` y módulos en `src/`
- Este archivo `docs/fase3_prompts.md` y las instrucciones de `README.md`

Con esto se cumple la forma de entrega del taller: **Markdown** para documentación y **código ejecutable** que produce respuestas ante los prompts.
