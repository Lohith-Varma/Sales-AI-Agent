"""Liveness and readiness endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from ai.api.dependencies import get_container
from ai.config.container import ApplicationContainer
from ai.schemas.responses_api import DependencyHealth, HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> HealthResponse:
    """Return liveness without forcing heavyweight model loading."""

    return HealthResponse(
        status="healthy",
        service=container.settings.app_name,
        version=container.settings.app_version,
        environment=container.settings.app_env.value,
    )


@router.get("/ready", response_model=HealthResponse)
async def readiness(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> HealthResponse:
    """Check access to persistent knowledge storage."""

    try:
        count = await container.vector_store.count()
        dependencies = {
            "chroma": DependencyHealth(status="healthy", detail=f"{count} indexed chunks")
        }
        status = "healthy"
    except Exception:
        dependencies = {"chroma": DependencyHealth(status="unavailable")}
        status = "unavailable"
    return HealthResponse(
        status=status,
        service=container.settings.app_name,
        version=container.settings.app_version,
        environment=container.settings.app_env.value,
        dependencies=dependencies,
    )


__all__ = ["router"]
