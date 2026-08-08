"""Application dependency-injection composition root."""

from __future__ import annotations

from dataclasses import dataclass

from ai.agents.crm.agent import CRMSummaryAgent
from ai.agents.crm.lead_scorer import LeadScorer
from ai.agents.entity.agent import EntityExtractionAgent
from ai.agents.guardrail.agent import GuardrailAgent
from ai.agents.guardrail.grounding import GroundingVerifier
from ai.agents.guardrail.policy import FinancialSafetyPolicy
from ai.agents.intent.agent import IntentDetectionAgent
from ai.agents.next_action.agent import NextBestActionAgent
from ai.agents.rag.agent import RAGRetrievalAgent
from ai.agents.rag.chunker import DocumentChunker
from ai.agents.rag.document_loader import KnowledgeDocumentLoader
from ai.agents.rag.indexer import KnowledgeIndexer
from ai.agents.rag.retriever import KnowledgeRetriever
from ai.agents.response.agent import ResponseGenerationAgent
from ai.agents.sentiment.agent import SentimentAgent
from ai.agents.speech.agent import SpeechToTextAgent
from ai.agents.speech.transcriber import ModelTranscriber
from ai.config.settings import Settings
from ai.models.embeddings import SentenceTransformerEmbeddingModel
from ai.models.llm import GeminiStructuredLLM
from ai.models.whisper import WhisperSpeechModel
from ai.orchestrator.graph import SalesCopilotWorkflow, build_graph
from ai.orchestrator.nodes import WorkflowNodes
from ai.services.chroma_store import ChromaVectorStore
from ai.services.conversation_store import InMemoryConversationStore
from ai.services.document_service import DocumentService
from ai.services.session_manager import SessionManager
from ai.services.core_persistence import CorePersistenceClient


@dataclass(frozen=True, slots=True)
class ApplicationContainer:
    """Owned application services exposed to FastAPI dependency functions."""

    settings: Settings
    workflow: SalesCopilotWorkflow
    document_service: DocumentService
    session_manager: SessionManager
    conversation_store: InMemoryConversationStore
    vector_store: ChromaVectorStore
    core_persistence: CorePersistenceClient


def build_container(settings: Settings) -> ApplicationContainer:
    """Construct the complete object graph without service-locator behavior."""

    llm = GeminiStructuredLLM(
        api_key=settings.gemini_api_key.get_secret_value(),
        model_name=settings.gemini_model,
        timeout_seconds=settings.gemini_request_timeout_seconds,
        max_retries=settings.gemini_max_retries,
    )
    embeddings = SentenceTransformerEmbeddingModel(
        model_name=settings.embedding_model,
        device=settings.embedding_device,
        batch_size=settings.embedding_batch_size,
        normalize=settings.normalize_embeddings,
    )
    vector_store = ChromaVectorStore(
        persist_directory=settings.chroma_persist_directory,
        collection_name=settings.chroma_collection,
    )
    speech = SpeechToTextAgent(
        ModelTranscriber(
            WhisperSpeechModel(model_name=settings.whisper_model, device=settings.whisper_device)
        )
    )
    intent = IntentDetectionAgent(llm, temperature=settings.gemini_analysis_temperature)
    sentiment = SentimentAgent(llm, temperature=settings.gemini_analysis_temperature)
    entity = EntityExtractionAgent(llm, temperature=settings.gemini_analysis_temperature)
    retriever = KnowledgeRetriever(
        embeddings=embeddings,
        vector_store=vector_store,
        maximum_context_characters=settings.rag_max_context_characters,
    )
    rag = RAGRetrievalAgent(retriever)
    response = ResponseGenerationAgent(
        llm,
        safe_fallback=settings.safe_fallback_response,
        temperature=settings.gemini_response_temperature,
    )
    next_action = NextBestActionAgent(llm, temperature=settings.gemini_analysis_temperature)
    guardrail = GuardrailAgent(
        grounding=GroundingVerifier(),
        policy=FinancialSafetyPolicy(),
        safe_fallback=settings.safe_fallback_response,
    )
    crm = CRMSummaryAgent(
        llm,
        LeadScorer(),
        temperature=settings.gemini_analysis_temperature,
    )
    nodes = WorkflowNodes(
        speech=speech,
        intent=intent,
        sentiment=sentiment,
        entity=entity,
        rag=rag,
        response=response,
        next_action=next_action,
        guardrail=guardrail,
        safe_fallback=settings.safe_fallback_response,
        rag_top_k=settings.rag_top_k,
        rag_fetch_k=settings.rag_fetch_k,
        rag_minimum_score=settings.rag_min_relevance_score,
        minimum_grounding_coverage=settings.min_grounding_coverage,
        minimum_agent_confidence=settings.min_agent_confidence,
    )
    workflow = SalesCopilotWorkflow(
        graph=build_graph(nodes),
        crm_agent=crm,
        live_timeout_seconds=settings.live_workflow_timeout_seconds,
        crm_timeout_seconds=settings.crm_workflow_timeout_seconds,
        safe_fallback=settings.safe_fallback_response,
    )
    loader = KnowledgeDocumentLoader(
        supported_extensions=settings.supported_document_extensions,
        maximum_bytes=settings.max_document_upload_bytes,
    )
    chunker = DocumentChunker(
        chunk_size=settings.document_chunk_size,
        chunk_overlap=settings.document_chunk_overlap,
    )
    indexer = KnowledgeIndexer(
        embeddings=embeddings,
        vector_store=vector_store,
        batch_size=settings.embedding_batch_size,
    )
    document_service = DocumentService(
        loader=loader,
        chunker=chunker,
        indexer=indexer,
        collection_name=settings.chroma_collection,
    )
    conversation_store = InMemoryConversationStore()
    session_manager = SessionManager(
        store=conversation_store,
        maximum_sessions=settings.max_concurrent_sessions,
        maximum_audio_bytes=settings.max_audio_buffer_bytes,
        maximum_duration_seconds=settings.session_max_duration_seconds,
    )
    core_persistence = CorePersistenceClient(
        base_url=settings.core_api_url,
        internal_api_key=(
            settings.internal_api_key.get_secret_value() if settings.internal_api_key else None
        ),
        timeout_seconds=settings.core_persistence_timeout_seconds,
        max_retries=settings.core_persistence_max_retries,
    )
    return ApplicationContainer(
        settings=settings,
        workflow=workflow,
        document_service=document_service,
        session_manager=session_manager,
        conversation_store=conversation_store,
        vector_store=vector_store,
        core_persistence=core_persistence,
    )


__all__ = ["ApplicationContainer", "build_container"]
