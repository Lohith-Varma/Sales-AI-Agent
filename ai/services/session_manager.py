"""Lifecycle manager for concurrent live-call sessions."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from ai.schemas.requests import CreateSessionRequest
from ai.services.audio_buffer import AudioBuffer
from ai.services.conversation_store import ConversationSession, ConversationStore
from ai.utils.exceptions import SessionLimitReachedError, SessionNotFoundError
from ai.utils.time import utc_now


@dataclass(slots=True)
class LiveSession:
    """Runtime-only resources associated with an active WebSocket call."""

    session_id: UUID
    audio_buffer: AudioBuffer
    created_at: datetime
    expires_at: datetime


class SessionManager:
    """Allocate, resolve, and release bounded live-session resources."""

    def __init__(
        self,
        *,
        store: ConversationStore,
        maximum_sessions: int,
        maximum_audio_bytes: int,
        maximum_duration_seconds: float,
    ) -> None:
        self._store = store
        self._maximum_sessions = maximum_sessions
        self._maximum_audio_bytes = maximum_audio_bytes
        self._maximum_duration_seconds = maximum_duration_seconds
        self._sessions: dict[UUID, LiveSession] = {}
        self._lock = asyncio.Lock()

    async def create(self, request: CreateSessionRequest) -> LiveSession:
        async with self._lock:
            if len(self._sessions) >= self._maximum_sessions:
                raise SessionLimitReachedError(self._maximum_sessions)
            now = utc_now()
            session_id = uuid4()
            live = LiveSession(
                session_id=session_id,
                audio_buffer=AudioBuffer(
                    configuration=request.audio_config,
                    maximum_bytes=self._maximum_audio_bytes,
                ),
                created_at=now,
                expires_at=now + timedelta(seconds=self._maximum_duration_seconds),
            )
            await self._store.create(
                ConversationSession(
                    session_id=session_id,
                    sales_agent_id=request.sales_agent_id,
                    external_lead_id=request.external_lead_id,
                    audio_config=request.audio_config,
                    language=request.language,
                    created_at=now,
                    updated_at=now,
                )
            )
            self._sessions[session_id] = live
            return live

    async def get(self, session_id: UUID) -> LiveSession:
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise SessionNotFoundError(session_id)
            if utc_now() >= session.expires_at:
                self._sessions.pop(session_id, None)
                raise SessionNotFoundError(session_id)
            return session

    async def close(self, session_id: UUID, *, ended_at: datetime | None = None) -> None:
        await self._store.finalize(session_id, ended_at or utc_now())
        async with self._lock:
            if self._sessions.pop(session_id, None) is None:
                raise SessionNotFoundError(session_id)

    async def active_count(self) -> int:
        async with self._lock:
            return len(self._sessions)


__all__ = ["LiveSession", "SessionManager"]
