# LecheFacil Backend

Minimal FastAPI backend MVP for multi-tenant dairy management.

## Features
- FastAPI + SQLAlchemy async stack with row-level tenancy
- JWT auth via OIDC + JWKS with basic RBAC
- Animals CRUD with optimistic locking and per-tenant uniqueness
- Clean architecture inspired layering
- CI pipeline with lint, tests, Docker build
- Terraform skeleton for cloud deployment

## Getting Started
```bash
poetry install
cp .env.example .env
poetry run alembic upgrade head  # migrations handled in CI/CD
poetry run uvicorn src.interfaces.http.main:app --reload
```

## Makefile Targets
- `make dev` runs the dev server
- `make lint` formats/lints with ruff
- `make test` runs pytest
- `make export-openapi` refreshes the OpenAPI schema file

## Testing
```bash
make test
```

## OpenAPI Export
```bash
make export-openapi
```

## CI/CD
CI workflow runs lint, tests, and Docker build. Deploy workflow demonstrates Terraform plan/apply.
