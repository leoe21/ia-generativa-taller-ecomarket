# Fase 1 - Seleccion y justificacion de componentes del sistema RAG

## Objetivo

Extender el asistente de EcoMarket para responder consultas abiertas con base en documentos internos, reduciendo alucinaciones y mejorando la trazabilidad de cada respuesta.

## Modelo de embeddings seleccionado

**Modelo elegido:** `intfloat/multilingual-e5-base`

### Justificacion

- **Rendimiento en espanol:** es un modelo multilingue robusto para tareas de recuperacion semantica, por lo que funciona bien con consultas de clientes en espanol.
- **Costo:** es open-source y puede ejecutarse localmente, lo que elimina costo por consulta y facilita su uso en un taller academico.
- **Precision:** ofrece un equilibrio adecuado entre calidad semantica y viabilidad local; supera alternativas demasiado pequenas cuando las preguntas cambian de formulacion.
- **Portabilidad:** se integra facilmente con LangChain y `sentence-transformers`, lo que simplifica el pipeline.

### Alternativas consideradas

- `paraphrase-multilingual-MiniLM-L12-v2`: mas liviano, pero normalmente con menor capacidad semantica.
- Embeddings propietarios por API: pueden ofrecer muy buena calidad, pero agregan dependencia de proveedor, costo variable y restricciones de cuota.

## Base de datos vectorial seleccionada

**Base elegida:** `ChromaDB`

### Justificacion

- **Facilidad de uso:** se integra directamente con LangChain y puede persistir localmente en disco.
- **Costo:** no requiere una cuenta cloud ni un servicio administrado para la demo.
- **Escalabilidad suficiente para el taller:** soporta bien una base documental pequena o mediana como la de EcoMarket.
- **Rapidez de iteracion:** permite reconstruir el indice con facilidad cuando cambian los documentos.

### Comparacion breve

| Opcion | Ventajas | Desventajas |
|--------|----------|-------------|
| `ChromaDB` | Local, simple, sin costo adicional, ideal para prototipos | Menor robustez operativa para cargas empresariales grandes |
| `Pinecone` | Alta escalabilidad, servicio administrado | Depende de cloud y de un plan con costo/cuotas |
| `Weaviate` | Flexible, potente y extensible | Mayor complejidad de despliegue y operacion |

## Arquitectura elegida para EcoMarket

1. Los documentos internos viven en `knowledge/`.
2. El sistema los convierte en fragmentos o chunks.
3. Cada chunk se transforma en embedding con `multilingual-e5-base`.
4. Los embeddings se almacenan en `ChromaDB`.
5. Ante una pregunta, se recuperan los fragmentos mas relevantes.
6. Solo con ese contexto se construye el prompt final para el LLM.
7. Si la evidencia recuperada es insuficiente, el asistente se abstiene de responder con seguridad y recomienda escalar a soporte humano.

## Decision final

Para este caso de uso, la combinacion **`multilingual-e5-base + ChromaDB`** ofrece el mejor balance entre precision en espanol, costo, facilidad de integracion y viabilidad para una entrega academica ejecutable.
