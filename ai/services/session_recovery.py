"""Recover a bounded live conversation context from the core call record."""

from __future__ import annotations

from uuid import UUID, uuid4

from ai.config.container import ApplicationContainer
from ai.schemas.enums import SpeakerRole
from ai.schemas.speech import TranscriptSegment
from ai.schemas.orchestration import CopilotResult


async def recover_session_context(
    container: ApplicationContainer,
    session_id: UUID,
    call_id: str | None,
) -> int:
    context = await container.core_persistence.fetch_session_context(call_id)
    rows = context.get("transcripts", []) if context else []
    segments: list[TranscriptSegment] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or not str(row.get("text") or "").strip():
            continue
        try:
            segment_id = UUID(str(row.get("segment_id")))
        except (TypeError, ValueError):
            segment_id = uuid4()
        speaker_value = str(row.get("speaker") or "unknown")
        speaker = (
            SpeakerRole.SALES_AGENT
            if speaker_value in {"agent", "sales_agent"}
            else SpeakerRole.CUSTOMER
            if speaker_value == "customer"
            else SpeakerRole.UNKNOWN
        )
        start = float(row.get("start_seconds") or index)
        end = float(row.get("end_seconds") or (start + 0.001))
        if end <= start:
            end = start + 0.001
        segments.append(
            TranscriptSegment(
                segment_id=segment_id,
                speaker=speaker,
                text=str(row["text"]).strip(),
                start_seconds=max(0.0, start),
                end_seconds=max(0.001, end),
                confidence=row.get("confidence"),
                language=str(row.get("language") or "unknown"),
                is_final=bool(row.get("is_final", True)),
            )
        )
    if segments:
        await container.conversation_store.append_transcript(session_id, tuple(segments))
    last_result = context.get("last_result") if context else None
    if isinstance(last_result, dict):
        session = await container.conversation_store.get(session_id)
        session.last_result = CopilotResult.model_validate(last_result)
        session.entities = session.last_result.entities
    return len(segments)


__all__ = ["recover_session_context"]
