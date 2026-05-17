# Fase 4: Despliegue de la aplicación

## 4.1 Streamlit frente a Gradio

Se optó de nuevo por **Streamlit** porque los talleres previos del curso ya usaban esa pila. No hubo un benchmark formal; la decisión respondió al **costo de migración** y a lo que hacía falta mostrar en la demostración.

| Criterio | Streamlit | Gradio |
|----------|-----------|--------|
| Continuidad del curso | Misma herramienta y flujo de trabajo | Reescribir UI por completo |
| Chat + pestañas + sidebar | Adecuado para guía y panel técnico | Chat fuerte; menos natural para varias áreas |
| Depuración en vivo | Expanders, JSON, dos vistas con `st.navigation` | Más limitado para auditoría |
| Despliegue público | Streamlit Cloud (sin Ollama local) | Hugging Face Spaces |

Streamlit reejecuta el script en cada interacción; `session_state` funciona, pero en una instancia compartida en la nube es fácil incurrir en problemas de concurrencia. Para una sustentación en un solo equipo no es crítico; en producción muchos equipos separarían API y front.

---

## 4.2 Interfaz: uso cotidiano y demostración técnica

Para esta entrega se requería un campo de texto y un área de respuesta accesibles. Eso se resolvió con `st.chat_input` e historial tipo chat. Además se incorporaron **dos vistas** en `app.py`:

- **Atención al cliente:** sin “tema detectado” ni JSON; errores genéricos. Aproxima lo que vería un comprador.
- **Sustentación académica:** pestañas Inicio / Cómo usar / Panel técnico; muestra ruta y `audit_log`.

| Aspecto | Implementación | Limitación |
|---------|----------------|------------|
| Texto libre del usuario | Chat en ambas vistas | Cooldown de 4 s (puede molestar en demo rápida) |
| Respuesta del agente | Burbujas de chat | Primera carga lenta (embeddings + Chroma) |
| Uso sin manual técnico | Ejemplos en sidebar + guía | Ollama debe estar instalado en la máquina demo |
| Claridad para no técnicos | Lenguaje natural en UI | El panel técnico sigue siendo denso |

Ocultar metadatos al usuario final es coherente con un producto real; para mostrar tools en vivo hace falta **cambiar de vista**. Una sola pantalla “pulida” no bastaría para evidenciar la arquitectura.

---

## 4.3 Ejecución local

La guía completa está en `README.md`. Resumen:

```text
ollama pull llama3.2:3b
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

**Incidencias observadas en pruebas:**

- Si Ollama no está activo en Windows, aparece error de conexión a `11434`; en la vista cliente el mensaje no siempre es explícito.
- La primera indexación de Chroma consume tiempo; conviene abrir la aplicación antes de la sustentación.
- Gemini en free tier devolvió 429 en algunas sesiones; por eso la demo se plantea con Ollama local.

---

## 4.4 Despliegue en la nube (opcional)

Streamlit Cloud puede alojar `app.py`, pero **no** incluye Ollama local ni el volumen de embeddings sin trabajo adicional (Docker en VPS, RunPod, etc.). La demostración funcional de esta entrega se planteó **en local**.

Un despliegue solo con APIs (Gemini/HF) cambiaría costo, latencia y tratamiento de datos personales; habría que actualizar la política de privacidad. Ese camino no se implementó aquí.

---

## 4.5 Guion de sustentación (15 minutos)

Secuencia sugerida que enlaza código, comportamiento y limitaciones del prototipo (no es un texto para leer literalmente):

| Min | Qué mostrar | Idea central |
|-----|-------------|--------------|
| 0–2 | Vista Sustentación, pestaña Cómo usar | Un chat, tres rutas; decisiones en código |
| 2–5 | Pagos o precio (RAG) | Evidencia en knowledge; abstención sin contexto |
| 5–9 | Devolución elegible (ej. 54321); Detalles técnicos | Tools en orden; LLM solo redacta |
| 9–12 | Devolución no elegible (higiene) | Rechazo de política, no fallo técnico |
| 12–14 | Pedido 12345 (tránsito) y devolución si aplica | Reembolso sin etiqueta |
| 14–15 | Fase 1 (tools + LangChain) y riesgos Fase 3 | Transparencia, logs, humano en excepciones |

Frases útiles en ensayos previos:

1. *“El router decide si es conocimiento, devolución o pedido; no es magia del modelo.”*
2. *“Las tools aplican la política; si Ollama falla, aún se muestra el resultado de la tool.”*
3. *“En producción esto no iría sin autenticación ni logs persistentes.”*

---

## 4.6 Antes de la sustentación

1. Ollama activo y modelo descargado.
2. Probar los ejemplos del sidebar en **Sustentación académica**.
3. Tener a mano las cuatro fases en `docs/proyecto_final/` (documentación escrita del repositorio, junto al código).

En síntesis, la aplicación permite una interacción exitosa de extremo a extremo en entorno local. No debe presentarse como producto terminado: es un **prototipo demostrable** con deudas de seguridad, escala y hosting que se documentan en la Fase 3.
