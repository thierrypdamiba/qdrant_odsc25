"""Query schemas"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class Source(BaseModel):
    doc_name: str
    doc_id: str
    chunk_text: str
    page: Optional[int] = None
    score: float
    image_url: Optional[str] = None


class QueryRequest(BaseModel):
    query: str
    mode: str = "auto"  # auto, local, internet, hybrid
    top_k: int = 5
    include_images: bool = False
    use_mmr: bool = False
    diversity: float = 0.5  # 0.0 = relevance, 1.0 = diversity
    enable_human_loop: bool = True  # Enable human-in-the-loop fallbacks


class ContextQuality(BaseModel):
    """Context quality evaluation scores"""
    overall_score: float
    vector_score: float
    coverage: float
    llm_confidence: float
    is_sufficient: bool
    reason: str


class PerformanceBreakdown(BaseModel):
    """Detailed timing breakdown"""
    total_ms: int
    cache_check_ms: Optional[int] = None
    embedding_ms: Optional[int] = None
    qdrant_search_ms: Optional[int] = None
    context_eval_ms: Optional[int] = None
    internet_search_ms: Optional[int] = None
    llm_generation_ms: Optional[int] = None
    cache_store_ms: Optional[int] = None


class QueryResponse(BaseModel):
    query_id: str
    query: str
    answer: str
    sources: List[Source]
    mode: str
    timestamp: datetime
    # Agent metadata (optional)
    cached: Optional[bool] = False
    cache_score: Optional[float] = None
    context_quality: Optional[ContextQuality] = None
    agent_decision: Optional[str] = None
    decision_log: Optional[List[str]] = None
    processing_time_ms: Optional[int] = None
    performance_breakdown: Optional[PerformanceBreakdown] = None
    # Cache timing breakdown (cloud inference)
    qdrant_server_ms: Optional[float] = None
    embedding_est_ms: Optional[float] = None
    search_est_ms: Optional[float] = None
    network_ms: Optional[float] = None
    cache_latency_ms: Optional[int] = None
    cloud_inference_used: Optional[bool] = None
    # Feedback metadata (optional)
    user_feedback: Optional[str] = None  # "thumbs_up", "thumbs_down", "mode_override"
    user_mode_override: Optional[str] = None  # Mode user selected if they overrode agent


class FeedbackRequest(BaseModel):
    """User feedback on query result"""
    query_id: str
    feedback: str  # "thumbs_up" or "thumbs_down"
    comment: Optional[str] = None  # Optional user comment


class ModeOverrideRequest(BaseModel):
    """User override of agent's mode decision"""
    query_id: Optional[str] = None
    selected_mode: str  # local, internet, hybrid
    reason: Optional[str] = None


class QueryHistoryResponse(BaseModel):
    queries: List[QueryResponse]
    total: int


