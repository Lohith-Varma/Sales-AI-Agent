"""Conversation session persistence abstraction and in-memory implementation."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol
from uuid import UUID

from ai.schemas.entities import CustomerEntities
from ai.schemas.speech import AudioConfiguration, TranscriptSegment
from ai.utils.exceptions import SessionNotFoundError
from ai.utils.time import utc_now


@dataclass(slots=True)
class ConversationSession:
    """Mutable server-side state for one call; never serialized directly."""

    session_id: UUID
    sales_agent_id: str
    external_lead_id: str | None
    audio_config: AudioConfiguration
    language: str | None
    created_at: datetime
    updated_at: datetime
    transcript: list[TranscriptSegment] = field(default_factory=list)
    entities: CustomerEntities = field(default_factory=CustomerEntities)
    ended_at: datetime | None = None


class ConversationStore(Protocol):
    """Persistence boundary for active conversation state."""

    async def create(self, session: ConversationSession) -> None: ...
    async def get(self, session_id: UUID) -> ConversationSession: ...
    async def append_transcript(
        self, session_id: UUID, segments: tuple[TranscriptSegment, ...]
    ) -> None: ...
    async def finalize(self, session_id: UUID, ended_at: datetime) -> ConversationSession: ...
    async def delete(self, session_id: UUID) -> None: ...
    async def count_active(self) -> int: ...


class InMemoryConversationStore:
    """Lock-protected session store suitable for one hackathon process."""

    def __init__(self) -> None:
        self._sessions: dict[UUID, ConversationSession] = {}
        self._lock = asyncio.Lock()

    async def create(self, session: ConversationSession) -> None:
        async with self._lock:
            if session.session_id in self._sessions:
                raise ValueError(f"session {session.session_id} already exists")
            self._sessions[session.session_id] = session

    async def get(self, session_id: UUID) -> ConversationSession:
        async with self._lock:
            try:
                return self._sessions[session_id]
            except KeyError as exc:
                raise SessionNotFoundError(session_id) from exc

    async def append_transcript(
        self, session_id: UUID, segments: tuple[TranscriptSegment, ...]
    ) -> None:
        async with self._lock:
            try:
                session = self._sessions[session_id]
            except KeyError as exc:
                raise SessionNotFoundError(session_id) from exc
            if session.ended_at is not None:
                raise ValueError("cannot append transcript to a finalized session")
            session.transcript.extend(segments)
            session.updated_at = utc_now()

    async def finalize(self, session_id: UUID, ended_at: datetime) -> ConversationSession:
        async with self._lock:
            try:
                session = self._sessions[session_id]
            except KeyError as exc:
                raise SessionNotFoundError(session_id) from exc
            session.ended_at = ended_at
            session.updated_at = utc_now()
            return session

    async def delete(self, session_id: UUID) -> None:
        async with self._lock:
            if self._sessions.pop(session_id, None) is None:
                raise SessionNotFoundError(session_id)

    async def count_active(self) -> int:
        async with self._lock:
            return sum(session.ended_at is None for session in self._sessions.values())


__all__ = ["ConversationSession", "ConversationStore", "InMemoryConversationStore"]
