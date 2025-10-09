# LecheFacil Backend

Backend sencillo basado en FastAPI para gestión lechera multi‑tenant.

## Requisitos
- Python 3.11+
- Poetry
- PostgreSQL

## Inicio rápido
```bash
# 1) Dependencias
poetry install

# 2) Variables de entorno
cp .env.example .env

# 3) Base de datos (migraciones)
poetry run alembic upgrade head

# 4) Levantar el servidor
make dev
# ó
# poetry run uvicorn src.interfaces.http.main:app --reload
```

## Útil
- Docs locales: http://localhost:8000/docs
- Pruebas: `make test`
