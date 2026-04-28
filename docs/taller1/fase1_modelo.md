# Propuesta de solución de IA generativa: EcoMarket

## Optimización de la atención al cliente en e-commerce

Este documento presenta una solución integral para el caso EcoMarket, alineada con los criterios del taller: **selección y justificación del enfoque de IA**, **análisis crítico (fortalezas, límites y ética)** y **diseño de prompts** demostrable en código.

---

## 1. Fase 1 — Selección y justificación del modelo de IA

### 1.1 Modelo y arquitectura seleccionados

Se propone una **arquitectura híbrida de Generación Aumentada por Recuperación (RAG)** sobre un **modelo de lenguaje de gran tamaño (LLM)**. En la implementación del taller, el motor de generación puede ser:

- **Principal (recomendado por el enunciado):** un modelo **open-source** ejecutado de forma local (por ejemplo **Llama 3.2** vía **Ollama**), para **evidenciar el impacto de los prompts** sin depender de cuotas de API.
- **Complementario (opcional):** un modelo vía **API** (por ejemplo **Google Gemini**), útil para comparar calidad, latencia y coste frente al modelo local.

El LLM **no sustituye** la base operativa: **recupera** información estructurada (pedidos, políticas) y **redacta** la respuesta al cliente con tono uniforme y reglas de negocio explícitas en el prompt.

### 1.2 Justificación técnica

| Criterio | Por qué encaja con EcoMarket |
|----------|------------------------------|
| **Precisión vs. fluidez** | Las consultas repetitivas (estado del pedido, devoluciones) exigen **datos correctos**; el RAG inyecta **solo el contexto recuperado** (p. ej. lista de pedidos y políticas) y el modelo se limita a formular la respuesta. Eso reduce alucinaciones sobre inventario o logística frente a un LLM “solo con memoria paramétrica”. |
| **Arquitectura** | **Retrieval:** consulta a una base de prueba (documento/JSON con pedidos). **Augmented generation:** el prompt incluye ese contexto + instrucciones (rol, tono, qué hacer si no hay match). |
| **Integración con datos de la empresa** | En producción, el mismo patrón se conectaría al **OMS/inventario/logística** en tiempo casi real; en el taller, el JSON actúa como **contrato** de cómo se expondrían esos datos al modelo. |
| **Escalabilidad** | El cuello de botella actual (24 h de respuesta) se ataca automatizando el **80%** de preguntas repetitivas; la capa de recuperación puede cachearse y paralelizarse; el LLM escala por API o por réplicas locales según política de coste. |
| **Costo y valor** | Un modelo open-source local **minimiza coste variable** por consulta (ideal para el ejercicio); un modelo de API de alto rendimiento puede justificarse en producción si el volumen y el SLA lo exigen. En ambos casos, el valor está en **liberar al equipo humano** para el **20%** de casos complejos. |
| **Facilidad de integración** | Encapsular RAG + LLM detrás de un servicio (p. ej. demo en **Streamlit**) es el mismo patrón que luego se expone a **chat, correo y redes** mediante APIs y conectores del CRM. |

### 1.3 Por qué no solo “un LLM general” sin RAG

Un LLM general puede sonar convincente pero **inventar** estados de pedido o plazos. El RAG **ancla** la respuesta en fuentes controladas por EcoMarket y permite **trazabilidad** (“esta respuesta se basó en estos registros/políticas”).
