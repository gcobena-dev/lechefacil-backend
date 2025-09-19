FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app

RUN pip install --no-cache-dir poetry==2.0.1

COPY pyproject.toml poetry.lock ./
RUN poetry install --no-root --only main

COPY src ./src
COPY scripts ./scripts

CMD ["uvicorn", "src.interfaces.http.main:app", "--host", "0.0.0.0", "--port", "8000"]
