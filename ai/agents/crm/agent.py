"""Post-call CRM summary agent with deterministic lead scoring."""

from datetime import date
from typing import Annotated

from pydantic import Field

from ai.agents.crm.lead_scorer import LeadScorer
from ai.models.llm import StructuredLLM
from ai.prompts.crm import CRM_SYSTEM_PROMPT
from ai.schemas.common import Confidence, SchemaModel
from ai.schemas.crm import CRMGenerationOutput, CRMGenerationRequest, CRMSummary
from ai.schemas.enums import LeadStatus
from ai.utils.json import dump_json


class _CRMDraft(SchemaModel):
    call_summary: Annotated[str, Field(min_length=1, max_length=5_000)]
    follow_up_date: date | None = None
    customer_concern: Annotated[str, Field(min_length=1, max_length=1_000)] | None = None
    lead_status: LeadStatus
    important_notes: Annotated[tuple[str, ...], Field(max_length=30)] = ()
    confidence: Confidence


class CRMSummaryAgent:
    name = "crm_summary"
    version = "1.0"

    def __init__(
        self,
        llm: StructuredLLM,
        lead_scorer: LeadScorer,
        *,
        temperature: float = 0.0,
    ) -> None:
        self._llm = llm
        self._lead_scorer = lead_scorer
        self._temperature = temperature

    async def run(self, request: CRMGenerationRequest) -> CRMGenerationOutput:
        draft = await self._llm.generate(
            system_prompt=CRM_SYSTEM_PROMPT,
            user_prompt=dump_json(request.model_dump(mode="json")),
            output_type=_CRMDraft,
            temperature=self._temperature,
        )
        summary = CRMSummary(
            call_summary=draft.call_summary,
            lead_score=self._lead_scorer.score(request),
            follow_up_date=draft.follow_up_date,
            customer_concern=draft.customer_concern,
            lead_status=draft.lead_status,
            important_notes=draft.important_notes,
        )
        return CRMGenerationOutput(crm_summary=summary, confidence=draft.confidence)


__all__ = ["CRMSummaryAgent"]
