from datetime import UTC, datetime, timedelta

from ai.agents.crm.lead_scorer import LeadScorer
from ai.schemas.crm import CRMGenerationRequest
from ai.schemas.entities import CustomerEntities
from ai.schemas.enums import IntentType, NextActionType, SentimentType


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
