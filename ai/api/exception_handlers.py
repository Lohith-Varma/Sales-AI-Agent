"""Central conversion of application failures to safe HTTP responses."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ai.config.logging import get_logger
from ai.schemas.enums import ErrorCode
from ai.schemas.responses_api import ErrorResponse
from ai.utils.exceptions import AppError


def register_exception_handlers(app: FastAPI) -> None:
    logger = get_logger("api.exceptions")

    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        logger.warning("request_failed", error_code=exc.code, retryable=exc.retryable)
        status = 503 if exc.retryable else 400
        payload = ErrorResponse(
            code=exc.code,
            message=exc.public_message,
            retryable=exc.retryable,
        )
        return JSONResponse(status_code=status, content=payload.model_dump(mode="json"))

    @app.exception_handler(Exception)
    async def handle_unexpected_error(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unexpected_request_failure", exception_type=type(exc).__name__)
        payload = ErrorResponse(
            code=ErrorCode.INTERNAL_ERROR,
            message="An unexpected service error occurred.",
            retryable=False,
        )
        return JSONResponse(status_code=500, content=payload.model_dump(mode="json"))


__all__ = ["register_exception_handlers"]
