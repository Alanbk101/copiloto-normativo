# Copiloto Normativo

Subes una ley, un reglamento o un contrato en PDF y le preguntas en lenguaje natural. Responde citando el artículo y la página exactos. Si la información no está en el documento, lo dice — no inventa.

![Demo](docs/demo.png)

## Stack

| Capa | Tecnología |
|---|---|
| API | FastAPI + SQLAlchemy 2.0 async |
| Base de datos | PostgreSQL + pgvector |
| Cola de tareas | Redis + arq |
| Frontend | Next.js 15 |
| Infraestructura | Docker Compose |
| LLM | Groq (qwen/qwen3.8-27b) |
| Embeddings | Jina AI (jina-embeddings-v3) |

## Cómo funciona

**Ingesta asíncrona**
El upload devuelve una respuesta inmediata. En segundo plano, un worker de arq parsea el PDF, lo parte en chunks por estructura del documento (artículos, capítulos, secciones), genera los embeddings con Jina AI y los persiste en Postgres. No se bloquea la API.

**Retrieval híbrido**
Cada consulta dispara dos búsquedas: full-text con `tsvector` en español e índice de coseno con `pgvector`. Ambas corren de forma secuencial (no en paralelo) porque comparten la sesión de SQLAlchemy, que no admite operaciones concurrentes. Los resultados se fusionan con Reciprocal Rank Fusion. Esto importa porque la búsqueda semántica sola pierde términos exactos — números de artículo, cifras, nombres propios de la norma.

**Generación con citas**
Los chunks recuperados se pasan al LLM con un prompt que impone dos restricciones: citar la fuente exacta (artículo + página) o declarar explícitamente que no encontró la información. No hay salida intermedia posible.

```
PDF upload
    │
    ▼
[Worker arq] → parseo → chunking por estructura → embeddings → Postgres
                                                                    │
                                                         ┌──────────┴──────────┐
                                                    full-text              vectorial
                                                    (tsvector)            (pgvector)
                                                         └──────────┬──────────┘
                                                                    │ RRF
                                                                    ▼
                                                               LLM + prompt
                                                                    │
                                                                    ▼
                                                        Respuesta con cita exacta
```

## Correrlo localmente

```bash
git clone https://github.com/Alanbk101/copiloto-normativo
cd copiloto-normativo
cp .env.example .env
# Edita .env con tus keys de Groq y Jina AI (ambas gratuitas)
docker compose up --build
```

Abre `http://localhost:3000`.

## Un bug real que resolví

**Síntoma:** el sistema daba timeout en absolutamente todo — uploads, consultas, el health check.

Mi primera suposición fue un bug en el código. Fui capa por capa:

1. Llamé a Groq directamente desde Python — respondió en 800ms.
2. Llamé al encoder de Jina directamente — sin problema.
3. Ejecuté el retrieval directo contra Postgres en un script — devolvió resultados.
4. Hice `curl localhost:8000/health` desde *dentro* del contenedor — 200 OK.

Cuando cada pieza funciona por separado pero el sistema falla completo, el problema no está en la aplicación — está en la red. Usé `netstat` para ver conexiones colgadas y `tasklist` para identificar procesos. El patrón apuntó a `wslrelay.exe`, el proceso que WSL2 usa para enrutar tráfico de Windows hacia los contenedores Docker. Estaba en un estado corrupto: aceptaba conexiones pero no las completaba.

Solución: `wsl --shutdown`. Reinicio limpio del stack de red de WSL2. El sistema quedó funcional.

La lección no es el comando — es el método: diagnóstico por eliminación, capa por capa, hasta que el punto de falla no tiene más dónde esconderse.

## Decisiones de diseño

**Chunking por estructura, no por tokens**
Partir documentos regulatorios cada N tokens garantiza que un artículo quede cortado a la mitad. Elegí parsear la estructura del documento (detectar encabezados de artículos, capítulos, anexos) y mantener cada unidad semántica completa. El retrieval es más preciso porque los chunks tienen coherencia legal, no arbitraria.

**Búsqueda híbrida**
La búsqueda vectorial captura intención semántica pero puede ignorar "Artículo 27", "fracción III" o una cifra específica. El full-text las atrapa exactamente. RRF combina ambas sin requerir calibrar pesos manuales.

**Interfaces para LLM y encoder**
Tanto el LLM como el encoder están detrás de un `Protocol` de Python. Esto me permitió migrar de Ollama local (donde tenía latencias de 40-60s en CPU) a Groq + Jina AI añadiendo dos implementaciones nuevas sin tocar la lógica de negocio — los tests existentes pasaron sin cambios.
