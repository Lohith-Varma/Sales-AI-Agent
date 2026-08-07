"""Controlled vocabulary used by agents and external API contracts."""

from enum import StrEnum


class SpeakerRole(StrEnum):
    """Participant responsible for a transcript segment."""

    CUSTOMER = "customer"
    SALES_AGENT = "sales_agent"
    UNKNOWN = "unknown"


class IntentType(StrEnum):
    """Supported customer intents for the Pay-in-3 sales conversation."""

    PRODUCT_INQUIRY = "product_inquiry"
    ELIGIBILITY = "eligibility"
    PRICING = "pricing"
    KYC = "kyc"
    OBJECTION = "objection"
    EXISTING_LOAN = "existing_loan"
    INTERESTED = "interested"
    FOLLOW_UP = "follow_up"
    REJECTION = "rejection"
    UNKNOWN = "unknown"


class SentimentType(StrEnum):
    """Supported customer emotion labels."""

    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    FRUSTRATED = "frustrated"
    CONFUSED = "confused"
    UNKNOWN = "unknown"


class EmploymentType(StrEnum):
    """Normalized employment classifications extracted from a conversation."""

    SALARIED = "salaried"
    SELF_EMPLOYED = "self_employed"
    CONTRACT = "contract"
    STUDENT = "student"
    RETIRED = "retired"
    UNEMPLOYED = "unemployed"
    OTHER = "other"
    UNKNOWN = "unknown"


class NextActionType(StrEnum):
    """Actions the co-pilot may recommend to the human representative."""

    EXPLAIN_BENEFITS = "explain_benefits"
    EXPLAIN_KYC = "explain_kyc"
    SCHEDULE_FOLLOW_UP = "schedule_follow_up"
    TRANSFER_TO_HUMAN_EXPERT = "transfer_to_human_expert"
    SEND_PRODUCT_BROCHURE = "send_product_brochure"
    START_APPLICATION = "start_application"
    ADDRESS_OBJECTION = "address_objection"
    ASK_CLARIFYING_QUESTION = "ask_clarifying_question"
    NO_ACTION = "no_action"


class LeadStatus(StrEnum):
    """CRM lifecycle status inferred at the end of a call."""

    NEW = "new"
    QUALIFYING = "qualifying"
    INTERESTED = "interested"
    FOLLOW_UP_REQUIRED = "follow_up_required"
    APPLICATION_READY = "application_ready"
    NOT_INTERESTED = "not_interested"
    DISQUALIFIED = "disqualified"
    ESCALATION_REQUIRED = "escalation_required"


class LeadTemperature(StrEnum):
    """Human-readable band derived from the deterministic lead score."""

    COLD = "cold"
    WARM = "warm"
    HOT = "hot"


class GuardrailViolationType(StrEnum):
    """Machine-readable reason a suggested response failed validation."""

    INVALID_SCHEMA = "invalid_schema"
    MISSING_CITATION = "missing_citation"
    UNKNOWN_CITATION = "unknown_citation"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    FINANCIAL_ADVICE = "financial_advice"
    GUARANTEED_APPROVAL = "guaranteed_approval"
    FABRICATED_PRICING = "fabricated_pricing"
    PROHIBITED_LANGUAGE = "prohibited_language"
    SENSITIVE_DATA_EXPOSURE = "sensitive_data_exposure"
    LOW_CONFIDENCE = "low_confidence"
    INSUFFICIENT_CONTEXT = "insufficient_context"


class DocumentType(StrEnum):
    """Knowledge-source formats supported by document ingestion."""

    PDF = "pdf"
    TEXT = "text"
    MARKDOWN = "markdown"
    FAQ = "faq"


class WorkflowStage(StrEnum):
    """Observable stages of a live LangGraph execution."""

    RECEIVED = "received"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    RETRIEVING = "retrieving"
    GENERATING = "generating"
    VALIDATING = "validating"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    FAILED = "failed"


class WebSocketMessageType(StrEnum):
    """Client-to-server WebSocket event types."""

    SESSION_START = "session_start"
    AUDIO_CONFIG = "audio_config"
    AUDIO_CHUNK = "audio_chunk"
    UTTERANCE_END = "utterance_end"
    CALL_END = "call_end"
    PING = "ping"


class WebSocketEventType(StrEnum):
    """Server-to-client WebSocket event types."""

    SESSION_READY = "session_ready"
    TRANSCRIPT = "transcript"
    COPILOT_RESULT = "copilot_result"
    CRM_SUMMARY = "crm_summary"
    STATUS = "status"
    ERROR = "error"
    PONG = "pong"


class ErrorCode(StrEnum):
    """Stable error codes safe to expose through HTTP and WebSocket APIs."""

    INVALID_REQUEST = "invalid_request"
    INVALID_AUDIO = "invalid_audio"
    MESSAGE_TOO_LARGE = "message_too_large"
    SESSION_NOT_FOUND = "session_not_found"
    SESSION_LIMIT_REACHED = "session_limit_reached"
    TRANSCRIPTION_FAILED = "transcription_failed"
    MODEL_UNAVAILABLE = "model_unavailable"
    RETRIEVAL_FAILED = "retrieval_failed"
    WORKFLOW_TIMEOUT = "workflow_timeout"
    INTERNAL_ERROR = "internal_error"


__all__ = [
    "DocumentType",
    "EmploymentType",
    "ErrorCode",
    "GuardrailViolationType",
    "IntentType",
    "LeadStatus",
    "LeadTemperature",
    "NextActionType",
    "SentimentType",
    "SpeakerRole",
    "WebSocketEventType",
    "WebSocketMessageType",
    "WorkflowStage",
]
