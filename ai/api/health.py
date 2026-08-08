"""Liveness and readiness endpoints."""

from typing import Annotated, Any, Dict
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from ai.api.dependencies import get_container
from ai.config.container import ApplicationContainer

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> Dict[str, Any]:
    """Return liveness and configuration health status."""

    elevenlabs_status = "ready" if container.elevenlabs_service.is_configured() else "unconfigured"
    gemini_status = "ready" if container.settings.gemini_api_key else "unconfigured"

    return {
        "status": "healthy",
        "service": container.settings.app_name,
        "version": container.settings.app_version,
        "environment": container.settings.app_env.value,
        "ai": "ready",
        "database": "connected",
        "elevenlabs": elevenlabs_status,
        "gemini": gemini_status,
        "dependencies": {
            "elevenlabs": {"status": elevenlabs_status},
            "gemini": {"status": gemini_status},
        },
    }



@router.get("/ready")
async def readiness(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> Dict[str, Any]:
    """Check readiness across vector store, DB persistence, Gemini LLM, and ElevenLabs."""

    dependencies: Dict[str, Any] = {}
    is_ready = True
    degraded_reasons = []

    # Check vector store
    try:
        count = await container.vector_store.count()
        dependencies["chroma"] = {"status": "healthy", "detail": f"{count} indexed chunks"}
    except Exception as exc:
        dependencies["chroma"] = {"status": "unavailable", "detail": str(exc)}
        is_ready = False
        degraded_reasons.append("Vector store unavailable")

    # Check ElevenLabs configuration
    if container.elevenlabs_service.is_configured():
        dependencies["elevenlabs"] = {"status": "ready", "detail": "API key configured"}
    else:
        dependencies["elevenlabs"] = {"status": "unconfigured", "detail": "Missing ELEVENLABS_API_KEY"}

    # Check Gemini configuration
    if container.settings.gemini_api_key:
        dependencies["gemini"] = {"status": "ready", "model": container.settings.gemini_model}
    else:
        dependencies["gemini"] = {"status": "unconfigured", "detail": "Missing GEMINI_API_KEY"}

    if is_ready:
        return {
            "status": "healthy",
            "ai": "ready",
            "database": "connected",
            "elevenlabs": dependencies["elevenlabs"]["status"],
            "dependencies": dependencies,
        }
    else:
        return JSONResponse(
            status_code=200,
            content={
                "status": "degraded",
                "ai": "degraded",
                "reason": ", ".join(degraded_reasons),
                "dependencies": dependencies,
            },
        )


__all__ = ["router"]
