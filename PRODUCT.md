# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Audiencia primaria: reclutadores e ingenieros que evalúan capacidades técnicas en RAG, búsqueda híbrida y diseño de sistemas. No hay usuario final regulatorio definido; el producto es en sí mismo la demostración técnica.

Audiencia secundaria hipotética (no confirmada para producción): profesionales legales o de compliance en México que consultan leyes, reglamentos o contratos en PDF de forma habitual.

## Product Purpose

Sistema de consulta RAG sobre documentos regulatorios mexicanos. El usuario sube un PDF (ley, reglamento, contrato) y hace preguntas en lenguaje natural. El sistema responde citando artículo y página exactos. Si la información no está en el documento, lo declara explícitamente — no inventa.

Propósito del despliegue: demo pública y portafolio en GitHub. El objetivo es demostrar un stack técnico completo y decisiones de ingeniería sólidas, no capturar usuarios regulatorios reales.

## Positioning

RAG con citación exacta obligatoria y sin alucinación — el LLM no puede producir una respuesta sin citar la fuente o declarar ausencia de información. Combina búsqueda vectorial (pgvector + Jina AI) y full-text (tsvector español) con Reciprocal Rank Fusion, y chunking por estructura legal (artículos, capítulos, secciones) en lugar de ventanas de tokens arbitrarias.

## Operating Context

- Documentos: PDFs regulatorios mexicanos — leyes, reglamentos, contratos
- Flujo: upload → ingesta asíncrona en background (arq worker) → consulta en lenguaje natural → respuesta con cita exacta
- Stack visible en el demo: FastAPI, Next.js 15, PostgreSQL + pgvector, Groq (qwen3.8-27b), Jina AI embeddings, Docker Compose
- Interfaz diseñada con estética de expediente legal mexicano: Spectral + IBM Plex Sans, paleta guinda/papel

## Capabilities and Constraints

- Solo responde sobre contenido presente en el documento subido
- Búsqueda híbrida: semántica (coseno) + full-text (tsvector español), fusión con RRF
- Chunking por estructura del documento, no por tokens
- Ingesta asíncrona; el upload no bloquea la API
- Sin autenticación de usuarios en la demo
- Sin multi-tenancy ni gestión de sesiones en v1
- LLM y encoder detrás de Protocol de Python — intercambiables sin tocar lógica de negocio

## Brand Commitments

- Nombre: Copiloto Normativo
- Estética: expediente legal / notarial mexicano — no SaaS genérico
- Paleta comprometida: guinda (#6E1423), papel (#F6F5F1), tinta (#111110), masa (#3A3530), linea (#D8D4CC), cita (#EDECE7)
- Tipografía comprometida: Spectral (serif, display) + IBM Plex Sans (sans, cuerpo)
- Terminología UI: §1 Expediente, §2 Consulta — lenguaje de documento formal, no "Upload" / "Chat"
- Voz: precisa, directa, sin adornos — refleja la naturaleza regulatoria del contenido

## Evidence on Hand

- README completo con arquitectura, decisiones de diseño y diagnóstico de bug real (wslrelay.exe)
- Código fuente completo en el repositorio
- Stack de evaluación: 46 tests
- No hay testimoniales, casos de uso reales, ni métricas de usuarios — esto es un demo técnico

## Product Principles

1. **Citación obligatoria, no opcional** — el sistema no produce respuesta sin fuente exacta; la confianza del usuario depende de ello.
2. **Diagnóstico por eliminación** — la arquitectura y el README demuestran razonamiento capa por capa, no soluciones de ensayo y error.
3. **Intercambiabilidad sin regresión** — LLM y encoder son intercambiables vía Protocol; los tests no cambian.
4. **Estética que comunica propósito** — el diseño de expediente legal no es decoración; señala al evaluador que el sistema entiende su dominio.
5. **Honestidad explícita** — cuando el documento no contiene la respuesta, el sistema lo dice; no hay salida intermedia.

## Accessibility & Inclusion

Sin requisito de accesibilidad específico establecido para la demo. El enfoque en reclutadores e ingenieros como audiencia primaria no descarta WCAG 2.1 AA como práctica de calidad.
