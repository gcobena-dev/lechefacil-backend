from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.application.errors import AppError, InfrastructureError

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:  # noqa: WPS430
        logger.info(
            "Application error handled: %s - %s (status: %d)",
            exc.code,
            exc.message,
            exc.status_code,
            extra={"path": request.url.path, "method": request.method},
        )
        payload = {"code": exc.code, "message": exc.message}
        if exc.details is not None:
            payload["details"] = exc.details
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:  # noqa: WPS430
        payload = {"code": "http_error", "message": exc.detail}
        return JSONResponse(status_code=exc.status_code, content=payload)

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:  # noqa: WPS430
        error = InfrastructureError("Unexpected server error")
        payload = {"code": error.code, "message": error.message}
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload)
