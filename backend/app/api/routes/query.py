"""Query routes"""
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.query import QueryRequest, QueryResponse, FeedbackRequest, ModeOverrideRequest
from app.core.auth import User
from app.core.deps import get_current_user
from app.services.rag import RAGService
from app.services.agent import AgenticRAG
from app.services.context_evaluator import ContextEvaluator
from app.services.semantic_cache import SemanticCache
from app.services.vector_store import QdrantVectorStore
from app.services.llm import GroqLLMService
from app.services.search import PerplexitySearchService
from app.services.document_processor import EmbeddingService
from app.core.config import settings
import uuid
from datetime import datetime

router = APIRouter(prefix="/query", tags=["query"])


async def get_agent_service() -> AgenticRAG:
    """Get Agentic RAG service with all components"""
    # Initialize real services
    vector_store = QdrantVectorStore(
        settings.qdrant_url, 
        settings.qdrant_api_key,
        cloud_inference=settings.qdrant_cloud_inference
    )
    llm_service = GroqLLMService(settings.groq_api_key)
    
    # Initialize search service only if API key is available
    if settings.perplexity_api_key:
        search_service = PerplexitySearchService(settings.perplexity_api_key)
    else:
        # Use mock search service if Perplexity key is not configured
        from app.services.mock_search import MockSearchService
        search_service = MockSearchService()
    
    # Embedding service
    embedding_service = EmbeddingService(settings.text_embedding_model)
    
    # RAG service
    rag_service = RAGService(
        vector_store=vector_store,
        llm_service=llm_service,
        search_service=search_service,
        embedding_service=embedding_service,
        org_id=settings.org_id
    )
    
    # Context evaluator
    context_evaluator = ContextEvaluator(llm_service)
    
    # Semantic cache
    semantic_cache = SemanticCache(
        vector_store=vector_store,
        embedding_service=embedding_service,
        org_id=settings.org_id,
        similarity_threshold=0.95,
        ttl_hours=24
    )
    
    # Initialize cache collection
    await semantic_cache.initialize()
    
    # Agentic RAG
    return AgenticRAG(
        rag_service=rag_service,
        context_evaluator=context_evaluator,
        semantic_cache=semantic_cache
    )


@router.post("/", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    current_user: User = Depends(get_current_user),
    agent: AgenticRAG = Depends(get_agent_service)
):
    """
    Intelligent query endpoint - agent automatically decides best approach
    
    Modes:
    - auto: Agent decides based on context quality (default)
    - local: Force local knowledge base
    - internet: Force internet search (requires permission)
    - hybrid: Force both (requires permission)
    """
    
    # Check permissions for forced modes
    if request.mode in ["internet", "hybrid"]:
        if not current_user.permissions.can_search_internet:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You don't have permission to use {request.mode} search"
            )
    
    # Use intelligent agent
    force_mode = None if request.mode == "auto" else request.mode
    
    result = await agent.query_intelligent(
        query=request.query,
        user=current_user,
        force_mode=force_mode,
        top_k=request.top_k,
        use_mmr=request.use_mmr,
        diversity=request.diversity
    )
    
    # Return response
    return QueryResponse(**result)


@router.post("/feedback")
async def submit_feedback(
    feedback: FeedbackRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Submit user feedback on a query result (thumbs up/down)
    """
    # TODO: Store feedback in database/cache for analytics
    # For now, just log it
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"User {current_user.user_id} feedback on query {feedback.query_id}: {feedback.feedback}")
    if feedback.comment:
        logger.info(f"Comment: {feedback.comment}")
    
    return {
        "status": "success",
        "message": "Feedback recorded",
        "query_id": feedback.query_id
    }


@router.post("/mode-override")
async def request_mode_override(
    override: ModeOverrideRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Request to override agent's mode decision during processing
    """
    # Check permissions
    if override.selected_mode in ["internet", "hybrid"]:
        if not current_user.permissions.can_search_internet:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You don't have permission to use {override.selected_mode} search"
            )
    
    # TODO: In a real implementation, this would trigger re-query with the new mode
    # For now, return the mode for the client to use
    return {
        "status": "success",
        "selected_mode": override.selected_mode,
        "message": f"Mode override requested: {override.selected_mode}"
    }


