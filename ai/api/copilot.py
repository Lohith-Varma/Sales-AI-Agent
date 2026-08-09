"""HTTP session and text-analysis endpoints."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends

from ai.api.dependencies import get_container
from ai.config.container import ApplicationContainer
from ai.orchestrator.state import LiveWorkflowInput
from ai.schemas.common import RequestContext
from ai.schemas.crm import CRMGenerationOutput, CRMGenerationRequest
from ai.schemas.enums import ErrorCode, SpeakerRole, WorkflowStage
from ai.schemas.orchestration import CopilotResult, WorkflowIssue
from ai.schemas.requests import (
    AnalyzeTextRequest,
    CompleteCallRequest,
    CreateSessionRequest,
)
from ai.schemas.responses_api import SessionCreatedResponse
from ai.schemas.speech import TranscriptSegment
from ai.services.session_recovery import recover_session_context
from ai.utils.exceptions import InvalidRequestError, PersistenceError
from ai.utils.time import utc_now

router = APIRouter(prefix="/copilot", tags=["copilot"])


@router.post("/sessions", response_model=SessionCreatedResponse)
async def create_session(
    request: CreateSessionRequest,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> SessionCreatedResponse:
    live = await container.session_manager.create(request)
    await container.core_persistence.link_session(
        request.external_lead_id, str(live.session_id)
    )
    await recover_session_context(container, live.session_id, request.external_lead_id)
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
        segment_id=result.request_id,
        speaker=SpeakerRole.CUSTOMER,
        text=request.customer_utterance,
        start_seconds=0,
        end_seconds=0.001,
        language=session.language or "unknown",
    )
    await container.conversation_store.append_transcript(request.session_id, (segment,))
    session.entities = result.entities
    session.last_result = result
    persisted = await asyncio.gather(
        container.core_persistence.persist_transcript(
            session.external_lead_id,
            [segment.model_dump(mode="json") | {"sequence_number": request.sequence_number}],
        ),
        container.core_persistence.persist_result(
            session.external_lead_id, result.model_dump(mode="json")
        ),
    )
    if not all(persisted):
        result = result.model_copy(
            update={
                "issues": (
                    *result.issues,
                    WorkflowIssue(
                        stage=WorkflowStage.COMPLETED,
                        code=ErrorCode.PERSISTENCE_FAILED,
                        message="The CRM write failed and can be retried.",
                        recoverable=True,
                    ),
                )
            }
        )
    return result


async def _execute_complete_call(
    session_id_value: UUID | str,
    ended_at_override: datetime | None,
    container: ApplicationContainer,
) -> CRMGenerationOutput:
    try:
        session_id = UUID(str(session_id_value))
    except ValueError as exc:
        raise InvalidRequestError("Session ID must be a valid UUID") from exc
    await container.session_manager.get(session_id)
    session = await container.conversation_store.get(session_id)
    last_result = session.last_result
    if last_result is None or not session.transcript:
        raise InvalidRequestError("Cannot summarize a call without analyzed transcript")
    ended_at = ended_at_override or utc_now()
    crm = await container.workflow.run_crm(
        CRMGenerationRequest(
            transcript="\n".join(
                f"{segment.speaker.value}: {segment.text}"
                for segment in session.transcript
            ),
            primary_intent=last_result.intent,
            final_sentiment=last_result.sentiment,
            entities=last_result.entities,
            recommended_action=last_result.next_best_action.action,
            call_started_at=session.created_at,
            call_ended_at=ended_at,
        )
    )
    persisted = await container.core_persistence.persist_crm_summary(
        session.external_lead_id,
        crm.crm_summary.model_dump(mode="json"),
        requires_human_review=crm.requires_human_review,
    )
    if not persisted:
        raise PersistenceError()
    await container.session_manager.close(session_id, ended_at=ended_at)
    return crm



@router.post("/complete", response_model=CRMGenerationOutput)
async def complete_call_body(
    request: CompleteCallRequest,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> CRMGenerationOutput:
    return await _execute_complete_call(request.session_id, request.ended_at, container)


@router.post("/sessions/{session_id}/complete", response_model=CRMGenerationOutput)
async def complete_call_path(
    session_id: UUID,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> CRMGenerationOutput:
    return await _execute_complete_call(session_id, None, container)


__all__ = ["router"]

