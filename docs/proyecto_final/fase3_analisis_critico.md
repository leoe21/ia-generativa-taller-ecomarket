# Fase 3: Análisis crítico y propuestas de mejora

Esta fase recoge riesgos, límites del prototipo y mejoras que quedaron fuera del alcance de la implementación. El foco no es repetir la arquitectura, sino evaluar qué ocurriría si la solución se expusiera a usuarios reales sin los controles de un entorno controlado.

---

## 3.1 Del texto generado a la acción ejecutada

En el Taller 2 el peor escenario habitual era la **alucinación**: inventar una política de devolución. En esta tercera entrega el riesgo sube de nivel: el sistema puede **simular** una etiqueta o un ticket de reembolso. Aunque sea un mock, el patrón reproduce lo que vería un cliente en producción: la sensación de que ya tiene un derecho operativo.

Riesgos considerados relevantes y cómo se abordaron (sin afirmar que el prototipo los elimina):

| Riesgo | Por qué importa | Medida en EcoMarket | Qué faltaría en producción |
|--------|-----------------|---------------------|----------------------------|
| Etiqueta indebida | Costo logístico, fraude | Workflow: etiqueta solo si `elegible` y pedido entregado | Validación en OMS, límites por usuario, antifraud |
| Política inventada por el LLM | Reclamos legales | Reglas en código; prompt atado al JSON de tools | Políticas versionadas, revisión legal |
| Fuga de datos de otro cliente | Daño legal y reputacional | Lookup por ID en JSON simulado sin autenticación | Login, scopes, auditoría de acceso |
| Opacidad (“¿qué hizo el bot?”) | Desconfianza | `audit_log` en vista de diagnóstico | Logs persistentes, ID de caso, SLA |
| Trato frío en rechazos | Churn, presión en redes | Mensajes empáticos + escalamiento humano | QA de tono, muestreo |
| Caída del LLM | Interrupción del servicio | Plantillas con datos de tools / JSON de pedido | Multi-proveedor, colas |
| Prompt injection | Bypass de políticas | Router + validación en tools | Sandboxing, allowlist |

**Principio adoptado:** las decisiones de negocio residen en **código y tools**; el LLM redacta. No es una postura anti-LLM: reconoce que un modelo de 3B parámetros no debería ser el último filtro antes de emitir una etiqueta.

El `audit_log` solo persiste en la sesión de Streamlit. Si el usuario cierra el navegador, no queda trazabilidad. Ante un reclamo del tipo “me generaron dos etiquetas”, con la implementación actual sería difícil reconstruir el caso.

---

## 3.2 Monitoreo: lo disponible frente a lo necesario

En la vista de diagnóstico se pueden abrir “Detalles técnicos” y ver pasos como `verificar_elegibilidad` o `generar_etiqueta`. Eso ayuda en la sustentación; **no sustituye** un sistema de monitoreo.

Esquema de registro orientativo para producción:

```json
{
  "timestamp": "ISO-8601",
  "session_id": "uuid",
  "route": "DEVOLUCION",
  "tools": [{"name": "verificar_elegibilidad_producto", "status": "ok", "latency_ms": 12}],
  "llm_provider": "ollama",
  "escalated_to_human": false
}
```

Métricas que convendría observar desde un piloto:

- Tasa de abstención RAG (respuestas sin evidencia suficiente).
- Proporción elegible / no elegible (¿política demasiado estricta?).
- Errores por tool y latencia p95 por ruta.
- Frecuencia de fallback sin LLM (señal de modelo o prompt inadecuado).

Alertas razonables:

- Pico de errores de API en pocos minutos.
- Generación de etiquetas por encima de un baseline (abuso o bug).
- Muchas conversaciones que terminan en “contacte soporte” (posible fallo del router).

Sin métricas, un router por reglas puede fallar en silencio (mensajes mal clasificados). Antes de ampliar tráfico, sería prudente etiquetar manualmente un conjunto de frases reales de soporte y medir precisión del clasificador.

---

## 3.3 Mejoras no implementadas en esta entrega

| Mejora | Motivo | Trade-off |
|--------|--------|-----------|
| Agente de **reemplazo** (orden en OMS) | Muchos reclamos no son devolución pura | Más tools = más superficie de error |
| **CRM** (notas en ticket) | Trazabilidad comercial | Integración y permisos |
| **Confirmación humana** antes de etiqueta | Reduce errores costosos | Fricción y colas |
| Router **híbrido** (reglas + LLM clasificador) | Mejor cobertura lingüística | Costo y latencia |
| **Rate limiting** en app pública | Abuso, costo de inferencia | Impacto en picos legítimos |
| **Human-in-the-loop** en casos límite | Calidad y cumplimiento | Escala 24/7 con costo |

Se implementó una versión acotada en `src/human_escalation.py`: después de un rechazo de política, si el cliente insiste o reintenta la devolución de forma repetida, el canal automático cierra el caso y asigna un ticket `SUP-…` para un agente humano. No se activa en el primer rechazo ni cuando solo faltan datos; busca el escenario en que la automatización ya no puede resolver sin generar fricción innecesaria.

En un despliegue serio, la prioridad debería ir a confirmación humana y logs persistentes antes que a más autonomía del modelo: en e-commerce, una devolución mal gestionada suele costar más que unos segundos de espera de un agente humano.

---

## 3.4 Conclusión

El prototipo sugiere que un asistente útil combina **RAG donde basta informar**, **tools donde hay que actuar** y **reglas donde el error es caro**. No demuestra que EcoMarket deba activar esto en producción sin supervisión.

Conclusiones que deja la implementación:

1. Un modelo pequeño local **puede redactar**, pero empujó a sacar pedidos y políticas fuera del LLM.
2. La “autonomía” de la literatura no coincide con lo que un negocio regulado necesita en devoluciones.
3. La interfaz dual (cliente / diagnóstico) ilustra transparencia: el usuario final no debe ver JSON, pero alguien interno debe poder auditar.

Un pasaje a producción exigiría identidad del cliente, políticas en base de datos, observabilidad real y escalamiento humano en excepciones. El LLM seguiría siendo un componente; no debería ser el dueño del proceso.
