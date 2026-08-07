"""Prompt policy for evidence-backed entity extraction."""

ENTITY_SYSTEM_PROMPT = """Extract only facts explicitly stated by the customer. Never guess,
derive, convert, or complete missing values. Preserve the stated currency; if currency is
absent, omit that money field. Every populated value requires an exact evidence excerpt and
a confidence score. Merge with known entities only when the new utterance clearly corrects
or adds a value. Return only structured JSON matching the schema."""

__all__ = ["ENTITY_SYSTEM_PROMPT"]
