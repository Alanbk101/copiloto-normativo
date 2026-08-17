.PHONY: up down logs migrate test shell

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
