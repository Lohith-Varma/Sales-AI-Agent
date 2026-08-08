"""HTTP session and text-analysis endpoints."""

from __future__ import annotations

import asyncio
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends

from ai.api.dependencies import get_container
from ai.config.container import ApplicationContainer
from ai.orchestrator.state import LiveWorkflowInput
from ai.schemas.common import RequestContext
from ai.schemas.enums import ErrorCode, WorkflowStage
from ai.schemas.orchestration import CopilotResult, WorkflowIssue
from ai.schemas.requests import AnalyzeTextRequest, CreateSessionRequest
from ai.schemas.requests import CompleteCallRequest
from ai.schemas.crm import CRMGenerationOutput, CRMGenerationRequest
from ai.utils.time import utc_now
from ai.schemas.responses_api import SessionCreatedResponse
from ai.schemas.speech import TranscriptSegment
from ai.services.session_recovery import recover_session_context

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
        # Analysis remains usable during a transient core outage. The caller can
        # surface the issue from core health and retry the utterance safely;
        # persistence endpoints are idempotent by segment and sequence IDs.
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


@router.post("/complete", response_model=CRMGenerationOutput)
async def complete_call(
    request: CompleteCallRequest,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> CRMGenerationOutput:
    await container.session_manager.get(request.session_id)
    session = await container.conversation_store.get(request.session_id)
    result = session.last_result
    if result is None or not session.transcript:
        from ai.utils.exceptions import InvalidRequestError

        raise InvalidRequestError("Cannot summarize a call without analyzed transcript")
    ended_at = request.ended_at or utc_now()
    crm = await container.workflow.run_crm(
        CRMGenerationRequest(
            transcript="\n".join(
                f"{segment.speaker.value}: {segment.text}" for segment in session.transcript
            ),
            primary_intent=result.intent,
            final_sentiment=result.sentiment,
            entities=result.entities,
            recommended_action=result.next_best_action.action,
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
        from ai.utils.exceptions import PersistenceError

        raise PersistenceError()
    await container.session_manager.close(request.session_id, ended_at=ended_at)
    return crm


__all__ = ["router"]
