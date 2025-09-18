POETRY = poetry
MODULE = src.interfaces.http.main:app

.PHONY: dev lint test export-openapi

dev:
	$(POETRY) run uvicorn $(MODULE) --reload

lint:
	$(POETRY) run ruff check src tests

test:
	$(POETRY) run pytest

export-openapi:
	./scripts/export_openapi.sh
