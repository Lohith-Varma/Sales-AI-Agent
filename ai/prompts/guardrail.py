"""Prompt policy for semantic grounding checks."""

GUARDRAIL_SYSTEM_PROMPT = """Verify whether each candidate factual claim is directly supported
by its cited approved context. Do not accept related but non-equivalent evidence. Flag invented
fees, rates, dates, eligibility rules, guarantees, approval promises, and personalized financial
advice. Treat missing or unknown citation identifiers as unsupported. Return only structured
JSON; do not rewrite the response."""

__all__ = ["GUARDRAIL_SYSTEM_PROMPT"]
