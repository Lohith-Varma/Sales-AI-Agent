"""FastAPI dependency accessors for the application container."""

from typing import Annotated, cast

from fastapi import Depends, Request

from ai.config.container import ApplicationContainer
from ai.orchestrator.graph import SalesCopilotWorkflow
from ai.services.document_service import DocumentService
from ai.services.session_manager import SessionManager


def get_container(request: Request) -> ApplicationContainer:
    return cast(ApplicationContainer, request.app.state.container)


def get_workflow(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> SalesCopilotWorkflow:
    return container.workflow


def get_document_service(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> DocumentService:
    return container.document_service


def get_session_manager(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> SessionManager:
    return container.session_manager


__all__ = ["get_container", "get_document_service", "get_session_manager", "get_workflow"]
