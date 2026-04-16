# EcoMarket — Solución integral de IA generativa

Aplicación en **Streamlit** para optimizar la atención al cliente en e-commerce (**Taller práctico #1**). Incluye documentación en Markdown (fases 1 y 2) y demo ejecutable con prompts y RAG (fase 3).

## Qué incluye

| Fase | Contenido | Archivo |
|------|-----------|---------|
| 1 | Selección y justificación del modelo (RAG + LLM, open-source / API opcional) | `docs/fase1_modelo.md` |
| 2 | Fortalezas, limitaciones y riesgos éticos | `docs/fase2_analisis_etico.md` |
| 3 | Ingeniería de prompts, encadenado en código y guía de despliegue | `docs/fase3_prompts.md` |

**Implementación:** `data/orders.json` (≥10 pedidos de prueba), `data/return_policies.json`, plantillas en `prompts/`, lógica en `src/` y UI en `app.py`.

---

## Requisitos

- **Python 3.10+**
- **Ollama** (recomendado para el taller; modelo open-source sin cuota de API)
- Opcional: **Google Gemini** si quieres probar la opción por API en la barra lateral

---

## Inicio rápido (recomendado: Ollama)

Sigue este orden: primero el motor local, luego el proyecto Python.

### 1) Ollama y el modelo

1. Instala Ollama: [https://ollama.com/download](https://ollama.com/download)
2. Deja Ollama en ejecución (servidor local en `http://localhost:11434`).
3. Descarga el modelo (una vez; **no** va dentro del `venv`):

   ```text
   ollama pull llama3.2:3b
   ```

4. Comprueba que aparece en la lista:

   ```text
   ollama list
   ```

### 2) Entorno virtual y dependencias (Python)

En la carpeta del proyecto (PowerShell en Windows):

```text
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3) Variables de entorno

Copia `.env.example` a `.env` y ajusta si cambias de modelo en Ollama:

```text
OLLAMA_MODEL=llama3.2:3b
# Opcional si el servidor no es el predeterminado:
# OLLAMA_BASE_URL=http://127.0.0.1:11434
```

`GOOGLE_API_KEY` solo es necesario si vas a usar **Gemini** en la app.

### 4) Ejecutar la aplicación

```text
streamlit run app.py
```

En el navegador, en la **barra lateral**, elige **“Open-source local (Ollama)”** y prueba las pestañas *Estado de pedido* y *Gestión de devoluciones*.

**Detalle de despliegue, flujo RAG y solución de problemas con Ollama:** ver `docs/fase3_prompts.md` (sección 3.4).

### Si aparece: «No fue posible conectar con Ollama…»

Eso significa que **no hay ningún servidor escuchando** en la dirección que usa la app (por defecto `http://127.0.0.1:11434`).

1. **Instala Ollama** desde [ollama.com/download](https://ollama.com/download) si aún no lo hiciste.
2. **Abre la aplicación Ollama en Windows** (Menú Inicio → *Ollama*). Debería quedar un icono en la **bandeja del sistema**; sin eso, el servicio no suele estar activo.
3. En **PowerShell**, comprueba:
   - `ollama list` → debe listar modelos (si está vacío: `ollama pull llama3.2:3b`).
   - `Invoke-WebRequest -Uri http://127.0.0.1:11434/api/tags -UseBasicParsing` → debe responder JSON, no error de conexión.
4. Si Ollama está en **otro puerto o PC**, define en `.env`: `OLLAMA_BASE_URL=http://IP:PUERTO` (sin barra final).
5. **VPN o firewall** a veces bloquean `localhost`; prueba desactivar la VPN un momento o permitir Ollama en el firewall de Windows.

---

## Opción alternativa: Gemini (API)

Si seleccionas **“Gemini API”** en la barra lateral:

- Configura en `.env` al menos `GOOGLE_API_KEY` (desde [Google AI Studio](https://aistudio.google.com)).
- **`GEMINI_MODEL`:** déjalo **vacío** para que la app pruebe en orden modelos **Flash** habituales del free tier (`gemini-1.5-flash`, `gemini-1.5-flash-latest`, `gemini-2.0-flash`, etc.). Si quieres uno concreto, pega el **ID exacto** que ves en el selector de modelo de AI Studio.
- El nombre del modelo no “gasta más cuota” que otro: cuenta cada llamada a la API. Si ves **429**, suele ser límite diario/por minuto del proyecto; prueba más tarde o usa **Ollama**.
- Si un modelo devuelve **404**, la app prueba el siguiente de la lista.
- Si aparece **cuota (429)** y no hay respuesta, la interfaz puede usar **respaldo** con los datos locales.

No subas `.env` al repositorio (está en `.gitignore`).

---

## Flujo de la aplicación

1. **Estado de pedido:** busca el ID en `data/orders.json`, arma el contexto y envía el prompt completo al modelo elegido.
2. **Devoluciones:** usa políticas en `data/return_policies.json`, clasificación en código y el prompt de devoluciones.
3. **Contexto y evidencias:** muestra los JSON de prueba para revisión académica.

---

## Notas académicas

- Prioriza **Ollama** para evidenciar el impacto de los prompts sin depender de cuota cloud.
- La IA automatiza consultas repetitivas (~80%); casos complejos o sensibles deben escalarse a soporte humano.
