from ai.orchestrator.routing import route_after_retrieval
from ai.schemas.rag import RetrievalOutput


def test_routes_to_fallback_when_context_is_insufficient() -> None:
    state = {"retrieval": RetrievalOutput(query="fees", sufficient_context=False, confidence=0)}
    assert route_after_retrieval(state) == "fallback_response"
