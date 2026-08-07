"""Deterministic and auditable lead scoring rules."""

from ai.schemas.crm import CRMGenerationRequest, LeadScore, LeadScoreFactor
from ai.schemas.enums import (
    IntentType,
    LeadTemperature,
    NextActionType,
    SentimentType,
)


class LeadScorer:
    """Calculate a stable score without delegating numeric judgment to an LLM."""

    def score(self, request: CRMGenerationRequest) -> LeadScore:
        factors = [LeadScoreFactor(name="base", points=20, rationale="Valid inbound lead")]
        intent_points = {
            IntentType.INTERESTED: 35,
            IntentType.ELIGIBILITY: 20,
            IntentType.PRICING: 15,
            IntentType.PRODUCT_INQUIRY: 10,
            IntentType.KYC: 10,
            IntentType.FOLLOW_UP: 10,
            IntentType.OBJECTION: -10,
            IntentType.EXISTING_LOAN: -5,
            IntentType.REJECTION: -40,
            IntentType.UNKNOWN: 0,
        }[request.primary_intent]
        factors.append(
            LeadScoreFactor(
                name="intent",
                points=intent_points,
                rationale=f"Primary intent is {request.primary_intent.value}",
            )
        )
        sentiment_points = {
            SentimentType.POSITIVE: 15,
            SentimentType.NEUTRAL: 5,
            SentimentType.CONFUSED: 0,
            SentimentType.NEGATIVE: -10,
            SentimentType.FRUSTRATED: -15,
            SentimentType.UNKNOWN: 0,
        }[request.final_sentiment]
        factors.append(
            LeadScoreFactor(
                name="sentiment",
                points=sentiment_points,
                rationale=f"Final sentiment is {request.final_sentiment.value}",
            )
        )
        populated = len(request.entities.populated_field_names())
        factors.append(
            LeadScoreFactor(
                name="information_completeness",
                points=min(15, populated * 3),
                rationale=f"Customer explicitly supplied {populated} tracked fields",
            )
        )
        action_points = 15 if request.recommended_action is NextActionType.START_APPLICATION else 0
        factors.append(
            LeadScoreFactor(
                name="application_readiness",
                points=action_points,
                rationale=f"Recommended action is {request.recommended_action.value}",
            )
        )
        score = min(100, max(0, sum(factor.points for factor in factors)))
        temperature = (
            LeadTemperature.COLD
            if score < 40
            else LeadTemperature.WARM
            if score < 70
            else LeadTemperature.HOT
        )
        return LeadScore(score=score, temperature=temperature, factors=tuple(factors))


__all__ = ["LeadScorer"]
