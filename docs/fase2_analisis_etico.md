# Propuesta de solución de IA generativa: EcoMarket

## 2. Fase 2 — Fortalezas, limitaciones y riesgos éticos

### 2.1 Capacidades: fortalezas y limitaciones

| Factor | Fortalezas | Limitaciones |
|--------|------------|--------------|
| **Operación y experiencia** | Disponibilidad **24/7**, tiempos de respuesta de **segundos** frente a **24 h**, consistencia de **tono y políticas**. | No reemplaza el juicio humano en **conflictos graves**, **situaciones legales** o **crisis de reputación** sin supervisión. |
| **Cobertura de consultas** | Automatiza de forma efectiva el **~80%** de preguntas repetitivas (pedidos, devoluciones, FAQs operativas). | El **~20%** restante suele requerir **empatía situacional**, negociación o excepciones no codificadas. |
| **Datos y calidad** | Si el retrieval es correcto, las respuestas sobre pedidos/políticas son **consistentes con la fuente**. | **Dependencia crítica** de la calidad, vigencia y gobernanza de los datos internos: *garbage in, garbage out*. |
| **Coste y despliegue** | Opción **open-source** reduce barrera económica y dependencia de un único proveedor para el taller. | Modelos locales exigen **hardware** y operación; APIs comerciales implican **cuotas, coste por token** y continuidad del servicio. |

### 2.2 Riesgos éticos y mitigación

| Riesgo | Descripción breve | Mitigación |
|--------|-------------------|------------|
| **Alucinaciones** | El modelo podría inventar plazos, cupones o estados no respaldados por datos. | RAG con **contexto explícito**, **temperatura baja**, instrucciones del tipo “usa solo el contexto”, validación **post-generación** (reglas o checks) y **escalamiento humano** si hay ambigüedad. |
| **Sesgos** | Respuestas injustas o estereotipadas hacia grupos de clientes. | **Pruebas con casos diversos**, revisión de prompts, políticas de contenido y supervisión humana en reclamos sensibles. |
| **Privacidad y tratamiento de datos** | Uso de direcciones, historial o datos personales en prompts o logs. | **Minimización** de datos, **pseudonimización/anonimización** donde aplique, retención acotada de logs, cumplimiento de marcos como **GDPR** (base legal, derechos del titular) y acuerdos con proveedores de API. |
| **Seguridad y abuso** | Inyección de instrucciones o extracción de políticas internas. | Separación de **rol de sistema** y **datos**, límites de contexto, filtros y **guardrails** de salida. |
| **Impacto laboral** | Miedo a desplazamiento de agentes de soporte. | Enfoque de **augmentación**: la IA resuelve lo repetitivo; los agentes pasan a **supervisión de calidad**, **casos complejos**, **mejora continua de prompts y bases de conocimiento** y **experiencia premium**. |
| **Transparencia y reclamos** | El cliente puede no saber que habla con un asistente automatizado. | **Divulgación clara** (“asistente con IA”), opción de **pasar a humano** y canales de escalamiento visibles. |
