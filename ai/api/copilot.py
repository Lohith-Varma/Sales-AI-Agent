"""HTTP session and text-analysis endpoints."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends

from ai.api.dependencies import get_container
from ai.config.container import ApplicationContainer
from ai.orchestrator.state import LiveWorkflowInput
from ai.schemas.common import RequestContext
from ai.schemas.orchestration import CopilotResult
from ai.schemas.requests import AnalyzeTextRequest, CreateSessionRequest
from ai.schemas.responses_api import SessionCreatedResponse
from ai.schemas.speech import TranscriptSegment

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.post("/sessions", response_model=SessionCreatedResponse)
async def create_session(
    request: CreateSessionRequest,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> SessionCreatedResponse:
    live = await container.session_manager.create(request)
    return SessionCreatedResponse(
        session_id=live.session_id,
        websocket_path=container.settings.websocket_path,
        expires_at=live.expires_at,
    )


@router.post("/analyze-text", response_model=CopilotResult)
async def analyze_text(
    request: AnalyzeTextRequest,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> CopilotResult:
    await container.session_manager.get(request.session_id)
    session = await container.conversation_store.get(request.session_id)
    context = tuple(
        segment.text
        for segment in session.transcript[-container.settings.transcript_context_turns :]
    )
    result = await container.workflow.run_live(
        LiveWorkflowInput(
            context=RequestContext(
                request_id=uuid4(),
                session_id=request.session_id,
                sequence_number=request.sequence_number,
            ),
            latest_customer_utterance=request.customer_utterance,
            conversation_context=context,
            known_entities=session.entities,
        )
    )
    segment = TranscriptSegment(
        text=request.customer_utterance,
        start_seconds=0,
        end_seconds=0.001,
        language=session.language or "unknown",
    )
    await container.conversation_store.append_transcript(request.session_id, (segment,))
    session.entities = result.entities
    return result


__all__ = ["router"]
