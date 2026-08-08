"""Validated HTTP and WebSocket inputs accepted by the API layer."""

from __future__ import annotations

from typing import Annotated, Literal, TypeAlias
from uuid import UUID

from pydantic import AwareDatetime, Field

from ai.schemas.common import SchemaModel
from ai.schemas.rag import MetadataScalar
from ai.schemas.speech import AudioConfiguration

ExternalReference = Annotated[
    str,
    Field(min_length=1, max_length=200, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:@/-]*$"),
]


class CreateSessionRequest(SchemaModel):
    """Request to allocate one isolated live-call co-pilot session."""

    sales_agent_id: ExternalReference
    external_lead_id: ExternalReference | None = None
    language: Annotated[str, Field(min_length=2, max_length=16)] | None = "en"
    audio_config: AudioConfiguration = Field(default_factory=AudioConfiguration)


class AnalyzeTextRequest(SchemaModel):
    """Text-only analysis input useful for testing and accessibility fallback."""

    session_id: UUID
    sequence_number: Annotated[int, Field(ge=0)]
    customer_utterance: Annotated[str, Field(min_length=1, max_length=10_000)]


class CompleteCallRequest(SchemaModel):
    """Request to finalize a call and produce its CRM summary."""

    session_id: UUID
    ended_at: AwareDatetime | None = None


class IngestDocumentsRequest(SchemaModel):
    """Options accompanying an approved knowledge-document upload."""

    replace_existing_source: bool = True
    title: Annotated[str, Field(min_length=1, max_length=500)] | None = None
    version: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    tags: Annotated[tuple[str, ...], Field(max_length=50)] = ()
    attributes: dict[str, MetadataScalar] = Field(default_factory=dict)


class SessionStartMessage(SchemaModel):
    """First WebSocket control message sent by the client."""

    type: Literal["session_start"] = "session_start"
    sales_agent_id: ExternalReference
    external_lead_id: ExternalReference | None = None
    language: Annotated[str, Field(min_length=2, max_length=16)] | None = "en"
    audio_config: AudioConfiguration = Field(default_factory=AudioConfiguration)
    access_token: Annotated[str, Field(min_length=20, max_length=4096)] | None = None


class AudioConfigMessage(SchemaModel):
    """Control message changing audio configuration before audio is buffered."""

    type: Literal["audio_config"] = "audio_config"
    audio_config: AudioConfiguration


class UtteranceEndMessage(SchemaModel):
    """Signal that buffered audio should be transcribed immediately."""

    type: Literal["utterance_end"] = "utterance_end"
    sequence_number: Annotated[int, Field(ge=0)]


class CallEndMessage(SchemaModel):
    """Signal that the call has ended and CRM generation should run."""

    type: Literal["call_end"] = "call_end"
    ended_at: AwareDatetime | None = None


class PingMessage(SchemaModel):
    """WebSocket heartbeat sent by the client."""

    type: Literal["ping"] = "ping"
    nonce: Annotated[str, Field(min_length=1, max_length=100)]


ClientControlMessage: TypeAlias = Annotated[
    SessionStartMessage | AudioConfigMessage | UtteranceEndMessage | CallEndMessage | PingMessage,
    Field(discriminator="type"),
]


__all__ = [
    "AnalyzeTextRequest",
    "AudioConfigMessage",
    "CallEndMessage",
    "ClientControlMessage",
    "CompleteCallRequest",
    "CreateSessionRequest",
    "ExternalReference",
    "IngestDocumentsRequest",
    "PingMessage",
    "SessionStartMessage",
    "UtteranceEndMessage",
]
