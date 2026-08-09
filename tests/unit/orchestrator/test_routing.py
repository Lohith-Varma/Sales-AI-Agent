import pytest

from ai.orchestrator.nodes import WorkflowNodes
from ai.orchestrator.routing import route_after_retrieval
from ai.schemas.common import TextEvidence
from ai.schemas.enums import IntentType, NextActionType
from ai.schemas.orchestration import IntentAnalysis
from ai.schemas.rag import RetrievalOutput


def test_routes_to_fallback_when_context_is_insufficient() -> None:
    state = {"retrieval": RetrievalOutput(query="fees", sufficient_context=False, confidence=0)}
    assert route_after_retrieval(state) == "fallback_response"


@pytest.mark.asyncio
async def test_follow_up_without_product_context_recommends_human_confirmed_follow_up() -> None:
    nodes = WorkflowNodes(
        speech=None,  # type: ignore[arg-type]
        intent=None,  # type: ignore[arg-type]
        sentiment=None,  # type: ignore[arg-type]
        entity=None,  # type: ignore[arg-type]
        rag=None,  # type: ignore[arg-type]
        response=None,  # type: ignore[arg-type]
        next_action=None,  # type: ignore[arg-type]
        guardrail=None,  # type: ignore[arg-type]
        safe_fallback="Verify with a product expert.",
        rag_top_k=5,
        rag_fetch_k=15,
        rag_minimum_score=0.48,
        minimum_grounding_coverage=1.0,
        minimum_agent_confidence=0.55,
    )
    output = await nodes.fallback_response(
        {
            "intent": IntentAnalysis(
                intent=IntentType.FOLLOW_UP,
                confidence=0.98,
                evidence=TextEvidence(text="think about it"),
            )
        }  # type: ignore[arg-type]
    )
    action = output["next_action"]
    assert action.action is NextActionType.SCHEDULE_FOLLOW_UP  # type: ignore[union-attr]
    assert action.requires_confirmation is True  # type: ignore[union-attr]
