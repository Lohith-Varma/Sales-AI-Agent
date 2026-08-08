"""FastAPI application factory and executable entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ai import __version__
from ai.api.copilot import router as copilot_router
from ai.api.exception_handlers import register_exception_handlers
from ai.api.health import router as health_router
from ai.api.knowledge import router as knowledge_router
from ai.api.websocket import router as websocket_router
from ai.config.container import build_container
from ai.config.logging import configure_logging, get_logger
from ai.config.settings import Settings, get_settings
from ai.security import verify_access_token


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construct an application with explicit, test-replaceable settings."""

    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.container = build_container(resolved_settings)
        if resolved_settings.app_env.value != "test":
            try:
                products = await app.state.container.core_persistence.fetch_approved_products()
                if products:
                    result = await app.state.container.document_service.ingest_product_records(products)
                    get_logger("application").info(
                        "core_knowledge_synchronized",
                        documents=result.document_count,
                        chunks=result.chunk_count,
                    )
            except Exception as exc:
                get_logger("application").warning(
                    "core_knowledge_sync_failed", exception_type=type(exc).__name__
                )
        get_logger("application").info(
            "application_started",
            version=__version__,
            environment=resolved_settings.app_env,
        )
        try:
            yield
        finally:
            await app.state.container.core_persistence.close()
            get_logger("application").info("application_stopped")

    docs_url = "/docs" if resolved_settings.enable_api_docs else None
    app = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        debug=resolved_settings.app_debug,
        docs_url=docs_url,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    @app.middleware("http")
    async def authenticate_ai_request(request: Request, call_next):
        public = request.url.path in {"/health", "/ready", "/docs", "/openapi.json"}
        if resolved_settings.auth_required and not public:
            authorization = request.headers.get("authorization", "")
            token = authorization.split(" ", 1)[1] if authorization.lower().startswith("bearer ") else None
            try:
                verify_access_token(
                    token,
                    resolved_settings.jwt_secret.get_secret_value()
                    if resolved_settings.jwt_secret
                    else None,
                )
            except (ValueError, TypeError):
                return JSONResponse(status_code=401, content={"detail": "Invalid or missing access token"})
        return await call_next(request)
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(copilot_router, prefix=resolved_settings.api_prefix)
    app.include_router(knowledge_router, prefix=resolved_settings.api_prefix)
    app.include_router(websocket_router)
    return app


app = create_app()


def run() -> None:
    """Run the ASGI service using environment-derived settings."""

    settings = get_settings()
    uvicorn.run(
        "ai.main:create_app",
        factory=True,
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
        log_config=None,
    )


if __name__ == "__main__":
    run()


__all__ = ["app", "create_app", "run"]
