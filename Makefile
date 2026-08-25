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

# Download qwen2.5:3b into the ollama_models volume (~2 GB, only needed once).
# The model persists across container rebuilds thanks to the named volume.
pull-model:
	docker compose exec ollama ollama pull qwen2.5:3b

# Run retrieval evaluation (requires documents loaded in the DB).
eval:
	docker compose exec api python evals/eval.py
