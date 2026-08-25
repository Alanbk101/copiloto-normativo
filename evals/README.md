# Evaluation Set — Copiloto Normativo

## What this measures

**Retrieval recall@K**: for each question, does `hybrid_search` return at least
one chunk whose content contains one of the expected keywords within the top-K results?

This is an objective metric — it tests the retrieval pipeline (embeddings + full-text +
RRF), independent of LLM output quality.

## Running the evaluation

```powershell
# With the stack running:
docker compose exec api python evals/eval.py

# With a different K:
docker compose exec api python evals/eval.py --top-k 10
```

Sample output (with real documents loaded):

```
══════════════════════════════════════════════════
  Retrieval Evaluation — questions.json
  Total questions: 30
──────────────────────────────────────────────────
  Recall@1   18/30  (60%)
  Recall@3   24/30  (80%)
  Recall@5   27/30  (90%)
──────────────────────────────────────────────────
  Failed questions (3):
    [q015] ¿Cómo se determina la base del impuesto predial?
    [q023] ¿Qué es el dictamen fiscal y quiénes están obligados...
    [q027] ¿Qué es la figura del establecimiento permanente...
══════════════════════════════════════════════════
```

## Replacing the example questions with real ones

`questions.json` contains 30 example questions based on a fictional (but
realistic) Mexican tax regulation. To use real questions:

1. Load your actual documents via `POST /documents`.
2. Use `GET /search?question=...` to find the real chunks that contain the
   correct answers.
3. For each question, fill in:
   - `expected_keywords`: 2–4 words that must appear in the correct chunk's
     content. Use short, distinctive phrases — avoid common words.
   - `expected_structure_path`: the `structure_path` of the correct chunk
     (e.g. `"Título II/Artículo 23"`). Optional — only used for documentation.
4. Remove the `"note"` field once the question is based on real data.

## Why keyword matching instead of exact chunk ID

Chunk IDs change every time a document is re-ingested. Keywords stay stable
across re-ingestions, making the eval reusable without manual updates.
The trade-off is that a false positive is possible if an unrelated chunk
happens to contain the keyword — mitigate by choosing distinctive phrases.
