#!/usr/bin/env bash
set -euo pipefail
OUT="docs/openapi/schema.json"
poetry run python - <<'PY'
import json
from pathlib import Path
from fastapi.openapi.utils import get_openapi
from src.interfaces.http.main import app

schema = get_openapi(
    title=app.title,
    version=app.version,
    routes=app.routes,
    description=app.description,
)
path = Path("docs/openapi")
path.mkdir(parents=True, exist_ok=True)
(path / "schema.json").write_text(json.dumps(schema, indent=2))
PY
echo "OpenAPI schema written to ${OUT}"
