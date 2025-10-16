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
- Comandos disponibles: `make help`

## Creación de Tenants

### Opción 1: Script CLI (Recomendado)
```bash
# Crear tenant con nuevo usuario
make create-tenant EMAIL=admin@example.com

# O usando Poetry directamente
poetry run python scripts/create_tenant.py --email admin@example.com
```

El script:
- Crea el usuario si no existe
- Crea el tenant y asocia el usuario como ADMIN
- Genera un token de un solo uso para establecer la contraseña
- Envía un email con el enlace (si está configurado)

### Opción 2: Endpoint HTTP
```bash
# Endpoint: POST /auth/register-tenant
# Header: X-Bootstrap-Key: <BOOTSTRAP_SECRET_KEY>

curl -X POST {host}/auth/register-tenant \
  -H "Content-Type: application/json" \
  -H "X-Bootstrap-Key: your-secret-key" \
  -d '{
    "email": "admin@example.com",
    "tenant_id": "optional-uuid-here"
  }'
```
