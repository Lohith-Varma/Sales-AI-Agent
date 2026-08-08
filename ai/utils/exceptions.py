"""Typed application exceptions with sanitized public error information."""

from __future__ import annotations

from typing import Final
from uuid import UUID

from ai.schemas.enums import ErrorCode

_DEFAULT_PUBLIC_MESSAGE: Final = "The request could not be completed."


class AppError(Exception):
    """Base class for expected operational and domain failures.

    ``message`` is intended for internal logs and must still avoid secrets and raw
    customer data. ``public_message`` is safe to expose through HTTP or WebSocket
    responses. Stack traces are never serialized by this class.
    """

    def __init__(
        self,
        message: str,
        *,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        public_message: str = _DEFAULT_PUBLIC_MESSAGE,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.public_message = public_message
        self.retryable = retryable


class ConfigurationError(AppError):
    """Raised when runtime configuration is invalid or incomplete."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message,
            public_message="The service is not configured correctly.",
        )


class InvalidRequestError(AppError):
    """Raised for a semantically invalid client request."""

    def __init__(self, message: str, *, public_message: str = "The request is invalid.") -> None:
        super().__init__(
            message,
            code=ErrorCode.INVALID_REQUEST,
            public_message=public_message,
        )


class InvalidAudioError(AppError):
    """Raised when an audio payload violates the negotiated stream format."""

    def __init__(
        self, message: str, *, public_message: str = "The audio payload is invalid."
    ) -> None:
        super().__init__(
            message,
            code=ErrorCode.INVALID_AUDIO,
            public_message=public_message,
        )


class MessageTooLargeError(AppError):
    """Raised before buffering an oversized HTTP or WebSocket payload."""

    def __init__(self, actual_bytes: int, maximum_bytes: int) -> None:
        super().__init__(
            f"Payload size {actual_bytes} bytes exceeds limit {maximum_bytes} bytes",
            code=ErrorCode.MESSAGE_TOO_LARGE,
            public_message=f"The payload exceeds the {maximum_bytes}-byte limit.",
        )
        self.actual_bytes = actual_bytes
        self.maximum_bytes = maximum_bytes


class SessionNotFoundError(AppError):
    """Raised when a session identifier is unknown or expired."""

    def __init__(self, session_id: UUID) -> None:
        super().__init__(
            f"Session {session_id} was not found",
            code=ErrorCode.SESSION_NOT_FOUND,
            public_message="The call session was not found or has expired.",
        )
        self.session_id = session_id


class SessionLimitReachedError(AppError):
    """Raised when an instance has no capacity for another live session."""

    def __init__(self, maximum_sessions: int) -> None:
        super().__init__(
            f"Concurrent session limit {maximum_sessions} reached",
            code=ErrorCode.SESSION_LIMIT_REACHED,
            public_message="The service is at capacity. Please retry shortly.",
            retryable=True,
        )
        self.maximum_sessions = maximum_sessions


class TranscriptionError(AppError):
    """Raised when the speech provider cannot transcribe a valid audio window."""

    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(
            message,
            code=ErrorCode.TRANSCRIPTION_FAILED,
            public_message="Audio transcription failed. Please retry this utterance.",
            retryable=retryable,
        )


class ModelUnavailableError(AppError):
    """Raised when an LLM or embedding model cannot serve a request."""

    def __init__(self, provider: str, message: str, *, retryable: bool = True) -> None:
        super().__init__(
            f"{provider} model unavailable: {message}",
            code=ErrorCode.MODEL_UNAVAILABLE,
            public_message="An AI model is temporarily unavailable.",
            retryable=retryable,
        )
        self.provider = provider


class RetrievalError(AppError):
    """Raised when the approved knowledge store cannot be queried."""

    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(
            message,
            code=ErrorCode.RETRIEVAL_FAILED,
            public_message="Approved product knowledge could not be retrieved.",
            retryable=retryable,
        )


class DocumentIngestionError(AppError):
    """Raised when an uploaded knowledge document cannot be safely indexed."""

    def __init__(self, message: str, *, public_message: str = "Document ingestion failed.") -> None:
        super().__init__(
            message,
            code=ErrorCode.INVALID_REQUEST,
            public_message=public_message,
        )


class WorkflowTimeoutError(AppError):
    """Raised when a graph execution exceeds its configured latency budget."""

    def __init__(self, timeout_seconds: float) -> None:
        super().__init__(
            f"Workflow exceeded its {timeout_seconds}-second timeout",
            code=ErrorCode.WORKFLOW_TIMEOUT,
            public_message="The co-pilot analysis timed out. Please retry.",
            retryable=True,
        )
        self.timeout_seconds = timeout_seconds


class PersistenceError(AppError):
    """Raised when a retry-bounded core CRM write does not succeed."""

    def __init__(self, message: str = "Core CRM persistence failed") -> None:
        super().__init__(
            message,
            code=ErrorCode.PERSISTENCE_FAILED,
            public_message="The CRM update could not be saved. Please retry.",
            retryable=True,
        )


__all__ = [
    "AppError",
    "ConfigurationError",
    "DocumentIngestionError",
    "InvalidAudioError",
    "InvalidRequestError",
    "MessageTooLargeError",
    "ModelUnavailableError",
    "PersistenceError",
    "RetrievalError",
    "SessionLimitReachedError",
    "SessionNotFoundError",
    "TranscriptionError",
    "WorkflowTimeoutError",
]
