#!/usr/bin/env bash
set -euo pipefail
poetry run uvicorn src.interfaces.http.main:app --reload
