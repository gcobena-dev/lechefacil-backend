POETRY = poetry
MODULE = src.interfaces.http.main:app

.PHONY: help dev lint test export-openapi create-tenant upgradedb migration

.DEFAULT_GOAL := help

help: ## Show this help message
	@echo "Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

dev: ## Start development server with hot reload
	$(POETRY) run uvicorn $(MODULE) --reload

lint: ## Run linter (ruff) on source code
	$(POETRY) run ruff --fix --unsafe-fixes . 
	$(POETRY) run ruff format .

test: ## Run all tests with pytest
	$(POETRY) run pytest

export-openapi: ## Export OpenAPI schema to docs/openapi/schema.json
	./scripts/export_openapi.sh

create-tenant: ## Create a new tenant (usage: make create-tenant EMAIL=admin@example.com)
ifndef EMAIL
	@echo "Error: EMAIL is required"
	@echo "Usage: make create-tenant EMAIL=admin@example.com"
	@exit 1
endif
	$(POETRY) run python scripts/create_tenant.py --email $(EMAIL)

upgradedb: ## Apply all pending database migrations
	$(POETRY) run alembic upgrade head

migration: ## Create a new migration (usage: make migration MESSAGE="description")
ifndef MESSAGE
	@echo "Error: MESSAGE is required"
	@echo "Usage: make migration MESSAGE=\"your migration description\""
	@exit 1
endif
	$(POETRY) run alembic revision --autogenerate -m "$(MESSAGE)"
