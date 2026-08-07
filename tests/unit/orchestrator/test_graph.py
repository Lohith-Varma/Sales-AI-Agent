from ai.orchestrator.graph import build_graph


class DummyNodes:
    async def transcribe(self, state: dict) -> dict:
        return {}

    async def detect_intent(self, state: dict) -> dict:
        return {}

    async def detect_sentiment(self, state: dict) -> dict:
        return {}

    async def extract_entities(self, state: dict) -> dict:
        return {}

    async def retrieve(self, state: dict) -> dict:
        return {}

    async def generate_response(self, state: dict) -> dict:
        return {}

    async def fallback_response(self, state: dict) -> dict:
        return {}

    async def recommend_action(self, state: dict) -> dict:
        return {}

    async def validate_response(self, state: dict) -> dict:
        return {}

    async def assemble(self, state: dict) -> dict:
        return {}


def test_graph_compiles_with_all_nodes() -> None:
    graph = build_graph(DummyNodes())  # type: ignore[arg-type]
    names = set(graph.get_graph().nodes)
    assert {"transcribe", "retrieve", "validate_response", "assemble"}.issubset(names)
