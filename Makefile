PYTHON ?= python
SEED_FILE ?= tests/fixtures/e2e/manifest.json

.PHONY: help install format format-check lint typecheck test test-backend test-integration coverage security verify migrate seed docker-config docker-build docker-up docker-down backup

help:
	@echo "install format format-check lint typecheck test coverage security verify"
	@echo "migrate seed docker-config docker-build docker-up docker-down backup"

install:
	$(PYTHON) -m pip install -e ".[dev]"
	npm ci

format:
	ruff format apps services packages tests

format-check:
	ruff format --check apps services packages tests

lint:
	ruff check apps services packages tests
	npm run lint

typecheck:
	mypy apps services packages
	npm run typecheck

test: test-backend
	npm test

test-backend:
	pytest -m "not integration" -q

test-integration:
	pytest -m integration -q

coverage:
	pytest -m "not integration" --cov=apps --cov=services --cov=packages --cov-report=term-missing
	npm run test:coverage

security:
	bandit -c pyproject.toml -r apps services packages/python
	pip-audit --requirement requirements.lock
	npm audit --omit=dev --audit-level=high

verify: format-check lint typecheck coverage security
	npm run build

migrate:
	alembic upgrade head

seed:
	portfolio-seed --file "$(SEED_FILE)"

docker-config:
	docker compose config --quiet
	docker compose run --rm --no-deps proxy caddy validate --config /etc/caddy/Caddyfile --adapter caddyfile

docker-build:
	docker compose build --pull

docker-up:
	docker compose up -d

docker-down:
	docker compose down --timeout 45

backup:
	docker compose --profile operations run --rm backup
