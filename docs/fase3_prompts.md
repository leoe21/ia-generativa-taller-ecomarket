# Fase 3 — Ingeniería de prompts y despliegue

Esta fase cumple el requisito del taller: **diseñar prompts efectivos** y **demostrar su impacto en código**, con una cadena clara entre instrucción, contexto recuperado (RAG) y respuesta del modelo. La aplicación está implementada en **Streamlit** (`app.py`).

Para el ejercicio académico se prioriza un modelo **open-source local** vía **Ollama** (nota del enunciado). La app también permite **Gemini por API** como opción opcional para comparar.

---

## 3.1 Prompt 1: consulta de estado de pedido

**Archivo:** `prompts/order_status_prompt.md`

**Variables que inyecta el código:** `{order_context}` (texto generado desde `data/orders.json` según el ID buscado) y `{tracking_number}`.

**Comportamiento esperado del modelo:**

- Actuar como agente de soporte de EcoMarket.
- Usar **solo** la información del contexto (mitiga alucinaciones sobre el pedido).
- Si no hay pedido en la base de prueba, pedir verificación amable del número.
- Si el pedido está **retrasado** (`retrasado: true` en JSON), disculparse y ofrecer **cupón del 5%**.
- Respuesta breve (máx. 120 palabras) y en español.

**Criterios del taller cubiertos:** número de seguimiento / ID de pedido, contexto con **al menos 10 pedidos** en la base simulada (`data/orders.json`), tono de agente y reglas de negocio explícitas.

---

## 3.2 Prompt 2: gestión de devoluciones (clasificación)

**Archivo:** `prompts/returns_prompt.md`

**Variables:** `{policy_context}` (JSON legible de `data/return_policies.json`), `{category}`, `{days_since_purchase}`.

**Lógica de negocio reflejada en datos y prompt:**

- **Perecederos / higiene:** no elegibles (motivo de seguridad/sanidad).
- **Ropa / accesorios:** elegibles dentro de **30 días**; se incluyen pasos orientativos (etiqueta, acopio, etc.).

La app además ejecuta una **clasificación previa** en `src/rag_engine.py` (`classify_return`) para mostrar en pantalla si el caso es elegible; el modelo redacta la respuesta empática final según el prompt y el contexto de políticas.

---

## 3.3 Cómo se encadena el RAG en el código

1. **Recuperación:** se leen `data/orders.json` y `data/return_policies.json` (simulan inventario/políticas).
2. **Construcción del prompt:** `app.py` carga las plantillas `.md`, rellena variables y envía un **único texto** al generador.
3. **Generación:** según la opción en la barra lateral:
   - **Open-source local (Ollama):** `src/open_source_client.py` → `POST` a `http://localhost:11434/api/generate` con el modelo definido en `OLLAMA_MODEL` (por defecto `llama3.2:3b`).
   - **Gemini API:** `src/llm_client.py` (opcional; requiere `GOOGLE_API_KEY`).
4. **Respaldo:** si Gemini devuelve error de **cuota (429)**, la interfaz puede mostrar una respuesta de respaldo basada en los mismos datos locales (sin depender del LLM en ese momento).

---

## 3.4 Despliegue y ejecución (modelo Ollama requerido para la demo principal)

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

## 3.5 Evidencia para entrega (repositorio)

Incluir en el repositorio:

- `prompts/order_status_prompt.md` y `prompts/returns_prompt.md`
- `data/orders.json` (≥10 pedidos) y `data/return_policies.json`
- `app.py` y módulos en `src/`
- Este archivo `docs/fase3_prompts.md` y las instrucciones de `README.md`

Con esto se cumple la forma de entrega del taller: **Markdown** para documentación y **código ejecutable** que produce respuestas ante los prompts.
