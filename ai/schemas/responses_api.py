"""HTTP responses and server-to-client WebSocket event contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated, Literal, TypeAlias
from uuid import UUID

from pydantic import AwareDatetime, Field

from ai.schemas.common import SchemaModel
from ai.schemas.crm import CRMSummary
from ai.schemas.enums import ErrorCode, WorkflowStage
from ai.schemas.orchestration import CopilotResult
from ai.schemas.rag import IngestionResult
from ai.schemas.speech import AudioConfiguration, TranscriptSegment


class DependencyHealth(SchemaModel):
    """Readiness state for one required application dependency."""

    status: Literal["healthy", "degraded", "unavailable"]
    detail: Annotated[str, Field(min_length=1, max_length=500)] | None = None


class HealthResponse(SchemaModel):
    """Application liveness or readiness response."""

    status: Literal["healthy", "degraded", "unavailable"]
    service: Annotated[str, Field(min_length=1, max_length=200)]
    version: Annotated[str, Field(min_length=1, max_length=50)]
    environment: Annotated[str, Field(min_length=1, max_length=50)]
    dependencies: dict[str, DependencyHealth] = Field(default_factory=dict)
    checked_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))


class SessionCreatedResponse(SchemaModel):
    """HTTP response returned after a live-call session is allocated."""

    session_id: UUID
    websocket_path: Annotated[str, Field(min_length=1, max_length=500)]
    expires_at: AwareDatetime


class DocumentIngestionResponse(SchemaModel):
    """HTTP response for one successful knowledge-ingestion request."""

    result: IngestionResult


class ErrorResponse(SchemaModel):
    """Sanitized error payload shared by HTTP endpoints."""

    code: ErrorCode
    message: Annotated[str, Field(min_length=1, max_length=500)]
    request_id: UUID | None = None
    retryable: bool = False


class SessionReadyEvent(SchemaModel):
    """Event confirming that a WebSocket session can accept audio."""

    type: Literal["session_ready"] = "session_ready"
    session_id: UUID
    audio_config: AudioConfiguration
    created_at: AwareDatetime = Field(default_factory=lambda: datetime.now(UTC))


class TranscriptEvent(SchemaModel):
    """Incremental transcript event emitted after Whisper inference."""

    type: Literal["transcript"] = "transcript"
    session_id: UUID
    sequence_number: Annotated[int, Field(ge=0)]
    segments: Annotated[tuple[TranscriptSegment, ...], Field(min_length=1)]


class CopilotResultEvent(SchemaModel):
    """Validated live co-pilot result for the sales-agent console."""

    type: Literal["copilot_result"] = "copilot_result"
    result: CopilotResult


class CRMSummaryEvent(SchemaModel):
    """Post-call CRM summary event requiring representative review."""

    type: Literal["crm_summary"] = "crm_summary"
    session_id: UUID
    crm_summary: CRMSummary
    requires_human_review: bool = True


class StatusEvent(SchemaModel):
    """Non-sensitive workflow progress notification."""

    type: Literal["status"] = "status"
    session_id: UUID
    stage: WorkflowStage
    message: Annotated[str, Field(min_length=1, max_length=300)]


class ErrorEvent(SchemaModel):
    """Sanitized WebSocket failure notification."""

    type: Literal["error"] = "error"
    code: ErrorCode
    message: Annotated[str, Field(min_length=1, max_length=500)]
    request_id: UUID | None = None
    retryable: bool = False


class PongEvent(SchemaModel):
    """WebSocket heartbeat response."""

    type: Literal["pong"] = "pong"
    nonce: Annotated[str, Field(min_length=1, max_length=100)]


class AudioStreamEvent(SchemaModel):
    """Audio payload containing ElevenLabs TTS response for browser playback."""

    type: Literal["audio_stream"] = "audio_stream"
    session_id: UUID
    audio_base64: str
    format: str = "audio/mpeg"
    sequence_number: Annotated[int, Field(ge=0)] = 0


ServerEvent: TypeAlias = Annotated[
    SessionReadyEvent
    | TranscriptEvent
    | CopilotResultEvent
    | CRMSummaryEvent
    | StatusEvent
    | ErrorEvent
    | PongEvent
    | AudioStreamEvent,
    Field(discriminator="type"),
]


__all__ = [
    "AudioStreamEvent",
    "CRMSummaryEvent",
    "CopilotResultEvent",
    "DependencyHealth",
    "DocumentIngestionResponse",
    "ErrorEvent",
    "ErrorResponse",
    "HealthResponse",
    "PongEvent",
    "ServerEvent",
    "SessionCreatedResponse",
    "SessionReadyEvent",
    "StatusEvent",
    "TranscriptEvent",
]

