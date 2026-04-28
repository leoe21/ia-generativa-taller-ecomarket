# Fase 2 - Creacion de la base de conocimiento

## Tipos de documentos seleccionados

Se construyo una base de conocimiento con al menos tres tipos de documentos relevantes para atencion al cliente:

1. `knowledge/politicas_operativas.md`
   Contiene reglas de devolucion, envio, facturacion, pagos y criterios de escalamiento.

2. `knowledge/faqs_ecomarket.json`
   Reune preguntas frecuentes estructuradas con respuesta directa.

3. `knowledge/catalogo_productos.csv`
   Representa un inventario simplificado con productos, categoria, precio, stock y disponibilidad.

4. `knowledge/guia_logistica.md`
   Complementa la cobertura de envios y los casos que deben pasar a soporte humano.

## Por que estos documentos son importantes

- **Politicas operativas:** permiten responder devoluciones, cupones, pagos y escalamiento.
- **FAQs:** cubren preguntas frecuentes en lenguaje cercano al cliente.
- **Catalogo:** habilita consultas sobre disponibilidad y caracteristicas basicas de productos.
- **Guia logistica:** mejora respuestas sobre tiempos, cobertura y limitaciones operativas.

## Estrategia de chunking

Se uso **segmentacion recursiva por texto** con `RecursiveCharacterTextSplitter`.

### Parametros definidos

- `chunk_size = 700`
- `chunk_overlap = 120`

### Justificacion

- Un chunk demasiado pequeno podria romper una politica o una respuesta frecuente.
- Un chunk demasiado grande haria mas costosa y menos precisa la recuperacion.
- El overlap conserva continuidad entre fragmentos consecutivos.
- La segmentacion recursiva respeta mejor secciones y parrafos que una division fija ciega.

## Como se indexan los documentos

1. Se detectan archivos compatibles dentro de `knowledge/` (`.md`, `.txt`, `.json`, `.csv`).
2. Cada archivo se transforma en uno o varios documentos `Document` de LangChain.
3. Los documentos se fragmentan con la estrategia de chunking seleccionada.
4. Cada fragmento se convierte en embedding con `intfloat/multilingual-e5-base`.
5. Los embeddings se almacenan en `ChromaDB` con persistencia local en `chroma_db/`.

## Impacto en el rendimiento del sistema RAG

La calidad de las respuestas del asistente depende directamente de:

- la claridad y actualidad de los documentos,
- el nivel de detalle disponible en cada fuente,
- la coherencia del chunking,
- y la capacidad del embedding para recuperar contenido relevante en espanol.

Por eso se eligieron documentos operativos y consultables, y no solo textos narrativos o ejemplos aislados.
