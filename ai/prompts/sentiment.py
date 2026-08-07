"""Prompt policy for customer-sentiment classification."""

SENTIMENT_SYSTEM_PROMPT = """Classify the current CUSTOMER emotion in a Pay-in-3 sales call.
Use only the schema labels. Distinguish confused from frustrated; use UNKNOWN when there is
not enough customer language. Evidence must be a short exact excerpt. Emotion may guide
conversation tone but must never imply credit eligibility. Return only structured JSON."""

__all__ = ["SENTIMENT_SYSTEM_PROMPT"]
