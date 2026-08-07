"""Real-time binary audio and co-pilot WebSocket endpoint."""

from __future__ import annotations

from contextlib import suppress
from datetime import datetime
from typing import cast
from uuid import UUID, uuid4

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import TypeAdapter, ValidationError

from ai.config.container import ApplicationContainer
from ai.config.logging import get_logger
from ai.orchestrator.state import LiveWorkflowInput
from ai.schemas.common import RequestContext, SchemaModel
from ai.schemas.crm import CRMGenerationRequest
from ai.schemas.enums import ErrorCode
from ai.schemas.orchestration import CopilotResult
from ai.schemas.requests import (
    AudioConfigMessage,
    CallEndMessage,
    ClientControlMessage,
    CreateSessionRequest,
    PingMessage,
    SessionStartMessage,
    UtteranceEndMessage,
)
from ai.schemas.responses_api import (
    CopilotResultEvent,
    CRMSummaryEvent,
    ErrorEvent,
    PongEvent,
    SessionReadyEvent,
    TranscriptEvent,
)
from ai.schemas.speech import AudioChunk, TranscriptionRequest, TranscriptSegment
from ai.services.audio_buffer import AudioBuffer
from ai.utils.exceptions import AppError, InvalidRequestError
from ai.utils.time import utc_now

router = APIRouter(tags=["websocket"])
_CONTROL_ADAPTER: TypeAdapter[ClientControlMessage] = TypeAdapter(ClientControlMessage)
_logger = get_logger("api.websocket")


async def _send_event(websocket: WebSocket, event: SchemaModel) -> None:
    await websocket.send_text(event.model_dump_json())


async def _process_audio(
    websocket: WebSocket,
    container: ApplicationContainer,
    session_id: UUID,
    sequence_number: int,
) -> CopilotResult | None:
    live = await container.session_manager.get(session_id)
    duration = live.audio_buffer.duration_seconds
    audio = await live.audio_buffer.drain()
    if not audio:
        return None
    session = await container.conversation_store.get(session_id)
    context = tuple(
        segment.text
        for segment in session.transcript[-container.settings.transcript_context_turns :]
    )
    result = await container.workflow.run_live(
        LiveWorkflowInput(
            context=RequestContext(
                request_id=uuid4(),
                session_id=session_id,
                sequence_number=sequence_number,
            ),
            transcription_request=TranscriptionRequest(
                session_id=session_id,
                audio_bytes=audio,
                audio_config=live.audio_buffer.configuration,
                language=session.language,
                context_hint=" ".join(context[-3:]) or None,
            ),
            conversation_context=context,
            known_entities=session.entities,
        )
    )
    segment = TranscriptSegment(
        text=result.latest_transcript,
        start_seconds=0,
        end_seconds=max(duration, 0.001),
        language=session.language or "unknown",
    )
    await container.conversation_store.append_transcript(session_id, (segment,))
    session.entities = result.entities
    await _send_event(
        websocket,
        TranscriptEvent(
            session_id=session_id, sequence_number=sequence_number, segments=(segment,)
        ),
    )
    await _send_event(websocket, CopilotResultEvent(result=result))
    return result


@router.websocket("/ws/copilot")
async def copilot_websocket(websocket: WebSocket) -> None:
    """Stream PCM16 frames and structured co-pilot events over one connection."""

    await websocket.accept()
    container = cast(ApplicationContainer, websocket.app.state.container)
    session_id: UUID | None = None
    frame_sequence = 0
    analysis_sequence = 0
    last_result: CopilotResult | None = None
    try:
        first = _CONTROL_ADAPTER.validate_json(await websocket.receive_text())
        if not isinstance(first, SessionStartMessage):
            raise InvalidRequestError("First WebSocket message must be session_start")
        live = await container.session_manager.create(
            CreateSessionRequest(
                sales_agent_id=first.sales_agent_id,
                external_lead_id=first.external_lead_id,
                language=first.language,
                audio_config=first.audio_config,
            )
        )
        session_id = live.session_id
        await _send_event(
            websocket,
            SessionReadyEvent(
                session_id=session_id,
                audio_config=live.audio_buffer.configuration,
            ),
        )
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
            binary = message.get("bytes")
            if binary is not None:
                if len(binary) > container.settings.max_websocket_message_bytes:
                    raise InvalidRequestError("WebSocket audio frame exceeds configured limit")
                await live.audio_buffer.append(
                    AudioChunk(
                        session_id=session_id,
                        sequence_number=frame_sequence,
                        audio_bytes=binary,
                    )
                )
                frame_sequence += 1
                if (
                    live.audio_buffer.duration_seconds
                    >= container.settings.transcription_window_seconds
                ):
                    last_result = await _process_audio(
                        websocket, container, session_id, analysis_sequence
                    )
                    analysis_sequence += 1
                continue

            text = message.get("text")
            if text is None:
                continue
            control = _CONTROL_ADAPTER.validate_json(text)
            if isinstance(control, PingMessage):
                await _send_event(websocket, PongEvent(nonce=control.nonce))
            elif isinstance(control, AudioConfigMessage):
                if frame_sequence != 0:
                    raise InvalidRequestError(
                        "Audio configuration cannot change after streaming starts"
                    )
                live.audio_buffer = AudioBuffer(
                    configuration=control.audio_config,
                    maximum_bytes=container.settings.max_audio_buffer_bytes,
                )
            elif isinstance(control, UtteranceEndMessage):
                last_result = (
                    await _process_audio(websocket, container, session_id, analysis_sequence)
                    or last_result
                )
                analysis_sequence += 1
            elif isinstance(control, CallEndMessage):
                last_result = (
                    await _process_audio(websocket, container, session_id, analysis_sequence)
                    or last_result
                )
                if last_result is None:
                    raise InvalidRequestError("Cannot summarize a call without a transcript")
                session = await container.conversation_store.get(session_id)
                ended_at: datetime = control.ended_at or utc_now()
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
                await _send_event(
                    websocket,
                    CRMSummaryEvent(
                        session_id=session_id,
                        crm_summary=crm.crm_summary,
                        requires_human_review=crm.requires_human_review,
                    ),
                )
                await container.session_manager.close(session_id, ended_at=ended_at)
                session_id = None
                break
    except WebSocketDisconnect:
        pass
    except ValidationError:
        await _send_event(
            websocket,
            ErrorEvent(code=ErrorCode.INVALID_REQUEST, message="Invalid WebSocket message."),
        )
    except AppError as exc:
        await _send_event(
            websocket,
            ErrorEvent(code=exc.code, message=exc.public_message, retryable=exc.retryable),
        )
    except Exception as exc:
        _logger.exception("websocket_failure", exception_type=type(exc).__name__)
        await _send_event(
            websocket,
            ErrorEvent(code=ErrorCode.INTERNAL_ERROR, message="The live session failed."),
        )
    finally:
        if session_id is not None:
            with suppress(AppError):
                await container.session_manager.close(session_id)
        with suppress(RuntimeError):
            await websocket.close()


__all__ = ["router"]
