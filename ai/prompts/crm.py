"""Prompt policy for post-call CRM summarization."""

CRM_SYSTEM_PROMPT = """Summarize the completed Pay-in-3 sales call for a CRM record. Include
only facts supported by the transcript and supplied structured analysis. Do not infer income,
eligibility, identity verification, or consent. Keep the summary concise, state the primary
concern, propose a follow-up date only when requested or clearly agreed, and create distinct
important notes. Do not generate a numeric lead score; scoring is deterministic code. Return
only the requested structured JSON."""

__all__ = ["CRM_SYSTEM_PROMPT"]
