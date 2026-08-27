.PHONY: up down logs migrate test shell pull-model eval

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	docker compose exec api alembic upgrade head

test:
	docker compose exec api pytest

shell:
	docker compose exec api bash

# Download the LLM model into the ollama_models volume (only needed once).
# The model persists across container rebuilds thanks to the named volume.
# Override OLLAMA_MODEL in .env to switch models without touching this file.
pull-model:
	docker compose exec ollama ollama pull $${OLLAMA_MODEL:-qwen2.5:1.5b}

# Run retrieval evaluation (requires documents loaded in the DB).
eval:
	docker compose exec api python evals/eval.py
