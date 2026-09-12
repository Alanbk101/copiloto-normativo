# Arquitectura del sistema

Este documento describe el diseño interno del Copiloto Normativo para quien
quiera entender las decisiones de ingeniería más allá del README. El README
cubre qué hace el sistema y cómo correrlo; este documento cubre por qué
está construido como está.

---

## 1. Visión general

El sistema es un pipeline RAG (Retrieval-Augmented Generation) especializado
en documentos normativos mexicanos. Lo que lo diferencia de un RAG genérico
son tres decisiones que interactúan entre sí: chunking por estructura legal
(no por tokens), retrieval híbrido que combina semántica y texto exacto, y
un prompt que elimina la zona gris entre "encontré algo" y "no sé".

```
HTTP POST /documents (PDF)
        │
        ▼
[FastAPI] — respuesta inmediata (202)
        │
        ▼ encola job
[Redis / arq worker]
        │
        ├─ pdfplumber: texto por página
        ├─ structure.py: detecta TÍTULO/CAPÍTULO/SECCIÓN/ARTÍCULO
        ├─ chunker.py: 1 bloque → 1 chunk (+ split si >4 000 chars)
        ├─ encoder.py: Jina AI → vector[1024]
        └─ Postgres: INSERT chunks (content + tsv + embedding)
                          │
HTTP POST /ask             │
        │                  │ (ya indexado)
        ▼                  │
[FastAPI]──────────────────┘
        │
        ├─ encode_query → vector[1024]
        ├─ _ft_search: tsvector + websearch_to_tsquery('spanish')  ─┐
        ├─ _vec_search: cosine_distance via pgvector               ─┤ RRF
        │                                                           ─┘
        ├─ top-5 chunks con structure_path + page_number
        ├─ prompt con fragmentos numerados + system.txt
        └─ Groq (qwen3.8-27b) → respuesta con citas exactas
```

Cada capa — ingesta, retrieval, generación — está desacoplada de sus
implementaciones concretas mediante interfaces (`Protocol` para LLM y encoder,
`AsyncSession` como contrato de la capa de datos), lo que permitió migrar
de proveedores locales a cloud sin tocar la lógica de negocio.

---

## 2. Flujo de ingesta en detalle

### 2.1 Extracción de texto (`parser.py`)

`pdfplumber` extrae el texto de cada página como `PageText(page_number, text)`.
Las páginas sin texto seleccionable (PDFs escaneados sin OCR) devuelven string
vacío en lugar de lanzar — la decisión de qué hacer con eso la toma quien llama.

No hay OCR. La limitación es deliberada: los documentos normativos oficiales
mexicanos (DOF, IMSS, SAT) siempre tienen texto seleccionable. Añadir Tesseract
añadiría una dependencia pesada para un caso de uso marginal.

### 2.2 Detección de estructura (`structure.py`)

Aquí está la apuesta central del diseño. En lugar de partir el texto cada N
tokens, el sistema detecta encabezados regulatorios con cuatro patrones regex
por nivel jerárquico:

| Nivel | Patrón | Ejemplo |
|-------|--------|---------|
| 1 | `^TITULO\s+\S+` | TÍTULO PRIMERO |
| 2 | `^CAPITULO\s+\S+` | CAPÍTULO III |
| 3 | `^SECCION\s+\d+` | SECCIÓN 2 |
| 4 | `^ARTICULO\s+(?:\d+\|[IVXLCDM]+)\b` | Artículo 27° |

Los patrones corren sobre texto normalizado (NFD → eliminar `Mn` →
colapsar espacios), así que "TÍTULO   PRIMERO", "Titulo Primero" y
"TITULO PRIMERO" producen el mismo match sin necesitar variantes de regex.

El detector mantiene un stack de ancestros y construye el `structure_path`
completo de cada bloque: `"TÍTULO PRIMERO > CAPÍTULO I > Artículo 15"`.
Ese path viaja con cada chunk hasta el prompt final y es lo que aparece
en la cita que el usuario ve.

Fallback: si no se detecta ningún encabezado (documento no estructurado
o completamente escaneado), el documento entero se convierte en un solo
bloque con `structure_path="Documento completo"`. El sistema degrada
gracefully en lugar de fallar.

### 2.3 Chunking (`chunker.py`)

Regla primaria: un bloque estructural → un chunk. Si el contenido del
bloque supera 4 000 caracteres (~1 000 tokens en español a ~4 chars/token),
el chunker intenta primero partir en párrafos (`\n\n`). Si un párrafo
individual excede 4 000 chars, aplica un corte duro por caracteres.

Todos los sub-chunks heredan el `structure_path` y `page_number` del bloque
padre. Esto garantiza que una cita "[Fuente: Artículo 27, página 14]"
sea válida aunque el artículo haya requerido tres chunks.

### 2.4 El worker de arq y la sesión de base de datos (`worker/jobs.py`)

El job `process_document` sigue un patrón de tres fases que resuelve un
bug real que produje durante el desarrollo:

**Fase 1** — abrir sesión, marcar documento como `processing`, commit, cerrar
sesión. El status es visible inmediatamente para polling.

**Fase 2a** — sin sesión abierta: ejecutar el pipeline puro de Python
(parse → structure → chunk) y llamar a `encode_passages` para generar
los embeddings. Este es el paso crítico: el encoding puede tardar varios
segundos (o minutos con el modelo local). Mantener una transacción abierta
durante ese tiempo es peligroso — PostgreSQL tiene `idle_in_transaction_session_timeout`
y los proxies de red matan conexiones inactivas. Una conexión muerta al
reconectarse borraba el estado pendiente de la sesión SQLAlchemy y los
chunks nunca se insertaban. La solución: la sesión no existe durante el
trabajo CPU/IO-bound.

**Fase 2b** — abrir sesión fresca solo para las operaciones de base de datos:
DELETE chunks huérfanos (idempotencia para reintentos de arq), INSERT nuevo
lote, UPDATE status del documento. La sesión vive milisegundos, no minutos.

El manejo de `CancelledError` (timeout del job de arq) usa `asyncio.shield`
para que la tarea de marcar el documento como `failed` sobreviva aunque la
tarea padre sea cancelada.

---

## 3. Flujo de retrieval en detalle

### 3.1 Por qué búsqueda híbrida

La búsqueda vectorial captura intención semántica pero puede ignorar
términos exactos: "Artículo 27", "fracción III", "150 UMAs". Un usuario
que pregunta "¿qué dice el artículo 27?" necesita que el sistema encuentre
ese artículo específico, no el más semánticamente similar. El full-text
con `tsvector` maneja exactamente esos casos. La combinación cubre el
espacio completo de consultas sin requerir que el usuario elija entre
dos modos.

### 3.2 Implementación (`retrieval/search.py`)

Cada consulta sigue esta secuencia:

1. `encode_query(question)` → vector[1024] con task adapter
   `retrieval.query` (el mismo modelo Jina pero con LoRA diferente
   al usado en indexación, optimizado para queries cortas).

2. `_ft_search`: ejecuta `websearch_to_tsquery('spanish', :question)` sobre
   la columna `tsv` con índice GIN. `websearch_to_tsquery` tolera input
   arbitrario — espacios, puntuación, stopwords — sin lanzar. Retorna
   top-20 por `ts_rank`.

3. `_vec_search`: `Chunk.embedding.cosine_distance(query_embedding)` vía
   la integración de pgvector con SQLAlchemy. El embedding viaja como
   parámetro tipado (`vector`), sin serializar a string. Índice HNSW.
   Retorna top-20 por distancia coseno.

Las dos búsquedas corren **secuencialmente**, no con `asyncio.gather`.
`AsyncSession` no soporta operaciones concurrentes sobre la misma conexión;
intentarlo produce un `MissingGreenlet` o un estado corrupto en el connection
pool. Dado que ambas son lookups de índice con latencia de milisegundos,
el overhead de secuenciarlas es despreciable.

### 3.3 Reciprocal Rank Fusion

RRF fusiona las dos listas rankeadas sin requerir calibrar pesos:

```
score(d) = Σᵢ  1 / (k + rankᵢ(d))
```

con k=60 (valor canónico de la literatura, previene que un rank 1 domine
desproporcionadamente). Un chunk que aparece en posición 1 de ambas listas
siempre supera a un chunk que solo aparece en una, sin importar su posición.
Los chunks que aparecen solo en una lista siguen siendo candidatos — no se
descartan.

El resultado final es un dict `{chunk_id: rrf_score}` ordenado por score.
Los metadatos del chunk (content, structure_path, page_number) se toman
del dict de metadatos construido uniendo ambos resultsets — cualquier
colisión es inocua porque ambos conjuntos llevan los mismos datos.

---

## 4. Flujo de generación

### 4.1 Construcción del contexto y el prompt

`answer_question` orquesta tres pasos:

1. Si retrieval devuelve cero chunks → retornar "No encontré esta información"
   sin llamar al LLM. Ningún token se consume.

2. Construir el contexto numerado:
   ```
   [1] Ruta: TÍTULO PRIMERO > Artículo 3 | Página: 4
   <contenido del chunk>

   [2] Ruta: TÍTULO PRIMERO > Artículo 27 | Página: 14
   <contenido del chunk>
   ```

3. Concatenar `system.txt` + contexto numerado + pregunta del usuario.
   El system prompt está en archivo (`prompts/system.txt`), nunca hardcodeado
   en la lógica — permite iterar el prompt sin tocar Python.

### 4.2 El system prompt

```
Eres un asistente jurídico-normativo. Responde ÚNICAMENTE con base en los
fragmentos de documento que se te proporcionan.

Para cada afirmación que hagas, cita su fuente usando exactamente este formato:
[Fuente: <structure_path>, página <page_number>]

Si los fragmentos no contienen la información, responde exactamente:
"No encontré esta información en los documentos disponibles."

Reglas: No inventes. No extrapoles. No uses conocimiento previo.
```

El prompt cierra la salida a exactamente dos estados: respuesta con cita,
o declaración de no encontrado. No hay tercer estado donde el modelo pueda
"ayudar de todas formas" con información no anclada al documento.

Las fuentes que el sistema reporta al frontend son todos los chunks
recuperados, no solo los que el modelo citó. Parsear el output del LLM
para detectar qué citas usó es frágil; las citas inline del modelo dan
al usuario el mapeo, y el frontend renderiza la lista completa.

### 4.3 El Protocol de LLM

```python
class LLMClient(Protocol):
    async def generate(self, prompt: str) -> str: ...
```

Cualquier objeto con ese método satisface el contrato —
structural typing de Python. `OllamaClient` y `GroqClient` lo
implementan sin heredar de una clase base. `LLMError` es la
excepción base que `answer_question` captura; las subclases
(`OllamaUnavailable`, `GroqUnavailable`) añaden contexto específico
del proveedor pero no cambian el comportamiento del caller.

Si el LLM falla, `answer_question` retorna un `AnswerResult` con
`found=False`, los sources del retrieval (que sí funcionó), y un
mensaje de error legible. El resultado parcial no se pierde.

### 4.4 El encoder como interfaz implícita

El encoder no tiene un Protocol explícito, pero sigue el mismo
principio: `encode_passages` y `encode_query` son funciones públicas
cuya implementación se selecciona por configuración
(`settings.embedding_provider`). El código de retrieval y de
ingesta nunca sabe si está hablando con Jina o con sentence-transformers.

---

## 5. Diagnóstico de infraestructura: el caso del wslrelay.exe

*(El README describe el método de diagnóstico. Aquí está el caso completo.)*

### Síntoma

Absolutamente todo daba timeout: uploads, consultas, el health check.
No había distinción entre endpoints — fallaba el sistema como unidad.

### Diagnóstico capa por capa

El patrón "todo falla, nada lanza excepción explicativa" apunta a red,
no a lógica. Procedí por eliminación:

**Capa 1 — LLM externo:**
```bash
python -c "
import asyncio, httpx
async def test():
    async with httpx.AsyncClient() as c:
        r = await c.post('https://api.groq.com/openai/v1/chat/completions',
                         headers={'Authorization': 'Bearer $GROQ_API_KEY'},
                         json={'model': 'qwen/qwen3.8-27b',
                               'messages': [{'role':'user','content':'ok'}]})
        print(r.status_code)
asyncio.run(test())
"
```
Resultado: 200 en ~800ms. Groq responde.

**Capa 2 — encoder externo:**
```bash
python -c "
import asyncio
from src.embeddings.encoder import encode_query
asyncio.run(encode_query('test'))
"
```
Sin problema.

**Capa 3 — base de datos:**
```bash
python -c "
import asyncio
from src.retrieval.search import hybrid_search
# script con sesión directa...
"
```
Devolvió resultados. Postgres vivo.

**Capa 4 — API dentro del contenedor:**
```bash
docker exec -it copiloto-api curl localhost:8000/health
```
`{"status": "ok"}` — 200ms. La API responde desde dentro.

**Conclusión de las capas:** cada componente funciona aislado. El
sistema falla solo cuando un proceso externo al contenedor intenta
conectarse. El problema está en el bridge de red entre Windows y
el stack Docker/WSL2.

**Inspección de red:**
```bash
# En PowerShell (host Windows)
netstat -ano | findstr ":8000"
```
Mostraba conexiones en estado `CLOSE_WAIT` acumuladas — el cliente
ya cerró su lado, el servidor nunca terminó de cerrar el suyo.

```bash
tasklist | findstr wslrelay
```
`wslrelay.exe` aparecía vivo pero con handles anómalos. Este proceso
es el relay que WSL2 usa para enrutar tráfico entre el espacio de red
de Windows y los contenedores Docker. Estaba en un estado donde
aceptaba conexiones TCP nuevas pero no completaba el handshake hacia
el destino — las conexiones entraban y nunca llegaban.

**Solución:**
```bash
wsl --shutdown
# Esperar ~10 segundos
docker compose up
```

`wsl --shutdown` termina todos los procesos WSL2 y reinicia el stack
de red desde cero, incluido wslrelay. Después del reinicio, las
conexiones fluían normalmente.

### Por qué es relevante más allá del anécdota

El diagnóstico reveló que el sistema de timeouts por capas que implementé
en los clientes HTTP (Groq: 60s read, Jina: 60s read, Ollama: 300s read)
estaba funcionando correctamente — el timeout que el usuario experimentaba
era el default del sistema operativo para conexiones TCP colgadas, no
una falla del código. El código no tenía nada que arreglar.

---

## 6. Decisiones de arquitectura

### ADR-1: Chunking por estructura regulatoria vs. por tokens

**Contexto:** Los RAG genéricos parten documentos cada N tokens con
overlap. Para documentos legales, esto garantiza que "El sujeto obligado
deberá... (continuación en otro chunk) ...reportar en un plazo de 30 días"
se indexe como dos unidades sin coherencia, generando citas imprecisas.

**Decisión:** Detectar la estructura del documento (TÍTULO/CAPÍTULO/
SECCIÓN/ARTÍCULO) y tratar cada unidad semántica como un chunk atómico.
El MAX_CHARS de 4 000 solo aplica como fallback para artículos
excepcionalmente largos, partiendo primero en párrafos.

**Alternativas consideradas:**
- Chunking fijo (512 tokens, 20% overlap): simple de implementar,
  recuperación imprecisa en textos legales.
- LlamaIndex/LangChain node parsers: introducen dependencias grandes
  para algo que se puede implementar con regex en ~100 líneas.

**Consecuencia:** El retrieval es más preciso pero el parser es
específico del formato de documentos normativos mexicanos. Un PDF
sin encabezados detectables cae al fallback de "documento completo",
que funciona pero pierde precisión.

---

### ADR-2: Retrieval híbrido con RRF vs. solo vectorial

**Contexto:** Una búsqueda vectorial pura con "¿qué dice el artículo 27?"
puede retornar artículos semánticamente relacionados pero no el 27
específico. Los usuarios de herramientas normativas hacen preguntas
con referencias exactas constantemente.

**Decisión:** Dos índices paralelos (GIN para tsvector, HNSW para
pgvector) fusionados con RRF. Ambos índices se mantienen en la
misma tabla de chunks; no hay segunda capa de infraestructura.

**Alternativas consideradas:**
- Solo vectorial: miss en términos exactos.
- Solo full-text: miss en paráfrasis semánticas ("¿cuál es el plazo
  para presentar la declaración anual?" no matchea "plazo: 30 días
  naturales a partir del cierre del ejercicio fiscal").
- BM25 manual: más complejo de implementar que `tsvector`+`ts_rank`,
  sin ventaja clara para este caso de uso.
- Fusión con pesos calibrados: requiere datos de evaluación para
  calibrar; RRF funciona bien sin ellos.

**Consecuencia:** La tabla de chunks tiene dos columnas de índice
(`tsv tsvector`, `embedding vector(1024)`). Cualquier cambio en la
dimensión del embedding requiere una migración de columna, no solo
reindexar.

---

### ADR-3: LLM y encoder detrás de interfaz (Protocol)

**Contexto:** Desarrollé el sistema con Ollama local (modelo qwen2.5:1.5b
en CPU) porque era la opción zero-costo inicial. La latencia de generación
era 40–60 segundos por consulta — inutilizable para demos.

**Decisión:** `LLMClient` es un `Protocol` de Python (structural typing).
`encode_passages`/`encode_query` son funciones con implementación
seleccionada por configuración. Ningún código de negocio importa
`OllamaClient` o `GroqClient` directamente.

**Alternativas consideradas:**
- ABC (clase base abstracta): más verboso, requiere herencia explícita.
  Protocol permite duck typing — clases de terceros satisfacen el
  contrato sin saber que existe.
- Sin abstracción: migrar de proveedor hubiera requerido editar
  `answer.py`, `search.py` y los tests.

**Consecuencia:** Migrar de Ollama+local a Groq+Jina fue añadir
dos clases nuevas y cambiar dos variables de entorno. Los tests
existentes pasaron sin modificación porque usan mocks que satisfacen
el Protocol.

---

### ADR-4: Sesión de base de datos no abierta durante el encoding

**Contexto:** La primera implementación del worker abría una `AsyncSession`
al inicio del job y la mantenía abierta durante todo el proceso: parseo,
embedding, insert. El encoding con el modelo local tardaba 2–5 minutos.
PostgreSQL (y el proxy de Docker) matan conexiones con transacciones
idle por más de cierto tiempo. Al reconectarse, SQLAlchemy perdía el
estado de la sesión y los chunks nunca llegaban a la base de datos — el
documento quedaba en status `processing` para siempre.

**Decisión:** Fase 2a (pipeline + embedding) se ejecuta sin ninguna sesión
abierta. La sesión se abre únicamente para las operaciones de base de datos
(Fase 2b), que son operaciones de millisegundos.

**Alternativas consideradas:**
- `idle_in_transaction_session_timeout = 0` en Postgres: deshabilita
  la protección en lugar de corregir la causa raíz.
- Keepalives de conexión: workaround frágil dependiente de configuración
  de infraestructura.
- Session pool con pre-ping: no resuelve el problema de la transacción
  idle, solo detecta conexiones muertas antes de usarlas.

**Consecuencia:** El código es más explícito sobre cuándo existe una
transacción activa. El pattern se documenta en el docstring del job.

---

## 7. Limitaciones conocidas y próximos pasos

**Sin autenticación.** Cualquier persona con acceso a la URL puede subir
documentos y hacer consultas. En producción esto requeriría al menos
autenticación por API key o JWT.

**Sin multi-tenancy.** Todos los documentos están en el mismo espacio.
Un usuario puede consultar documentos subidos por otro (o por nadie —
no hay concepto de "mi documento"). La tabla `documents` no tiene
`user_id`.

**Chunking solo para documentos normativos mexicanos.** Los patrones
regex de `structure.py` detectan TÍTULO/CAPÍTULO/SECCIÓN/ARTÍCULO en
español. Un PDF en inglés, o con estructura diferente (un contrato de
common law, por ejemplo), cae al fallback de documento completo y pierde
precisión en el retrieval.

**Sin OCR.** PDFs escaneados sin capa de texto son inútiles para el sistema.

**Sin streaming.** La respuesta del LLM llega completa antes de enviarse
al cliente. Para preguntas que generan respuestas largas, el usuario espera
sin feedback.

**Qué haría distinto con más tiempo:**
- Evaluar el retrieval sistemáticamente con un conjunto de preguntas de
  referencia antes de iterar sobre parámetros (k en RRF, top_n, MAX_CHARS).
  Actualmente los valores son razonables pero no están medidos.
- Streaming de la respuesta del LLM hacia el frontend para mejorar
  perceived latency.
- Un modo de "carga por lotes" para organizaciones que necesiten indexar
  decenas de documentos al mismo tiempo.
