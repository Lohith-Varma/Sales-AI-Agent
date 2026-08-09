from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from ai.agents.crm.agent import CRMSummaryAgent
from ai.agents.crm.lead_scorer import LeadScorer
from ai.schemas.crm import CRMGenerationRequest
from ai.schemas.entities import CustomerEntities
from ai.schemas.enums import IntentType, LeadStatus, NextActionType, SentimentType


def test_lead_score_is_deterministic() -> None:
    started = datetime.now(UTC)
    request = CRMGenerationRequest(
        transcript="customer: I am interested",
        primary_intent=IntentType.INTERESTED,
        final_sentiment=SentimentType.POSITIVE,
        entities=CustomerEntities(),
        recommended_action=NextActionType.START_APPLICATION,
        call_started_at=started,
        call_ended_at=started + timedelta(minutes=2),
    )
    first = LeadScorer().score(request)
    second = LeadScorer().score(request)
    assert first == second
    assert first.score == 85


@pytest.mark.asyncio
async def test_crm_agent_supplies_deterministic_date_for_required_follow_up(
    fake_llm_factory: type,
) -> None:
    started = datetime.now(UTC)
    request = CRMGenerationRequest(
        transcript="customer: I'll think about it.",
        primary_intent=IntentType.FOLLOW_UP,
        final_sentiment=SentimentType.NEUTRAL,
        entities=CustomerEntities(),
        recommended_action=NextActionType.SCHEDULE_FOLLOW_UP,
        call_started_at=started,
        call_ended_at=started + timedelta(minutes=2),
    )
    draft = SimpleNamespace(
        call_summary="Customer asked for time to consider the product.",
        follow_up_date=None,
        customer_concern="Needs more time",
        lead_status=LeadStatus.FOLLOW_UP_REQUIRED,
        important_notes=(),
        confidence=0.9,
    )

    result = await CRMSummaryAgent(fake_llm_factory(draft), LeadScorer()).run(request)

    assert result.crm_summary.lead_status is LeadStatus.FOLLOW_UP_REQUIRED
    assert result.crm_summary.follow_up_date is not None
    assert result.requires_human_review is True
