"""FastAPI application factory and executable entry point."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai import __version__
from ai.api.copilot import router as copilot_router
from ai.api.exception_handlers import register_exception_handlers
from ai.api.health import router as health_router
from ai.api.knowledge import router as knowledge_router
from ai.api.websocket import router as websocket_router
from ai.config.container import build_container
from ai.config.logging import configure_logging, get_logger
from ai.config.settings import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construct an application with explicit, test-replaceable settings."""

    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.container = build_container(resolved_settings)
        get_logger("application").info(
            "application_started",
            version=__version__,
            environment=resolved_settings.app_env,
        )
        yield
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
    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(copilot_router, prefix=resolved_settings.api_prefix)
    app.include_router(knowledge_router, prefix=resolved_settings.api_prefix)
    app.include_router(websocket_router)
    return app


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


__all__ = ["create_app", "run"]
