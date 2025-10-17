"""Streaming query endpoint with real-time progress updates"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from app.schemas.query import QueryRequest
from app.core.auth import User
from app.core.deps import get_current_user
from app.services.vector_store import QdrantVectorStore
from app.services.llm import GroqLLMService
from app.services.search import PerplexitySearchService
from app.services.document_processor import EmbeddingService
from app.services.rag import RAGService
from app.services.context_evaluator import ContextEvaluator
from app.services.semantic_cache import SemanticCache
from app.core.config import settings
import json
import time
import asyncio

router = APIRouter(prefix="/query", tags=["query"])


async def stream_agent_query(
    query: str,
    mode: str,
    top_k: int,
    current_user: User
):
    """Stream query processing steps in real-time"""
    
    start_time = time.time()
    
    def send_event(event_type: str, data: dict):
        """Helper to format SSE events"""
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    
    try:
        # Initialize services
        yield send_event("status", {
            "step": "init",
            "message": "🚀 Initializing services...",
            "timestamp": time.time() - start_time
        })
        
        vector_store = QdrantVectorStore(settings.qdrant_url, settings.qdrant_api_key)
        llm_service = GroqLLMService(settings.groq_api_key)
        search_service = PerplexitySearchService(settings.perplexity_api_key)
        
        embedding_service = EmbeddingService(
            settings.text_embedding_model,
            settings.image_embedding_model
        )
        
        rag_service = RAGService(
            vector_store=vector_store,
            llm_service=llm_service,
            search_service=search_service,
            embedding_service=embedding_service,
            org_id=settings.org_id
        )
        
        context_evaluator = ContextEvaluator(llm_service)
        semantic_cache = SemanticCache(
            vector_store=vector_store,
            embedding_service=embedding_service,
            org_id=settings.org_id
        )
        await semantic_cache.initialize()
        
        # Step 1: Check cache
        yield send_event("status", {
            "step": "cache_check",
            "message": "🔍 Checking semantic cache...",
            "timestamp": time.time() - start_time
        })
        
        cache_start = time.time()
        cached_result = await semantic_cache.get(query, current_user.user_id)
        cache_time = int((time.time() - cache_start) * 1000)
        
        if cached_result:
            yield send_event("status", {
                "step": "cache_hit",
                "message": f"⚡ CACHE HIT! (similarity: {cached_result['cache_score']:.3f})",
                "time_ms": cache_time,
                "timestamp": time.time() - start_time
            })
            
            yield send_event("result", {
                **cached_result,
                "processing_time_ms": int((time.time() - start_time) * 1000)
            })
            return
        
        yield send_event("status", {
            "step": "cache_miss",
            "message": "❌ Cache MISS - processing query...",
            "time_ms": cache_time,
            "timestamp": time.time() - start_time
        })
        
        # Step 2: Embed query
        yield send_event("status", {
            "step": "embedding",
            "message": "🔤 Generating query embedding...",
            "timestamp": time.time() - start_time
        })
        
        embed_start = time.time()
        query_vector = embedding_service.embed_text_query(query)
        embed_time = int((time.time() - embed_start) * 1000)
        
        yield send_event("status", {
            "step": "embedding_done",
            "message": f"✓ Query embedded",
            "time_ms": embed_time,
            "timestamp": time.time() - start_time
        })
        
        # Step 3: Search Qdrant
        yield send_event("status", {
            "step": "qdrant_search",
            "message": "📚 Searching Qdrant vector database...",
            "timestamp": time.time() - start_time
        })
        
        search_start = time.time()
        filter_classified = not current_user.permissions.can_access_classified
        collection_name = f"{settings.org_id}_text"
        
        results = await vector_store.search(
            collection_name=collection_name,
            query_vector=query_vector,
            top_k=top_k
        )
        
        if filter_classified:
            results = [r for r in results if "classified" not in r["payload"].get("tags", [])]
        
        search_time = int((time.time() - search_start) * 1000)
        
        yield send_event("status", {
            "step": "qdrant_done",
            "message": f"✓ Found {len(results)} sources from Qdrant",
            "time_ms": search_time,
            "num_sources": len(results),
            "timestamp": time.time() - start_time
        })
        
        # Convert to Source objects
        from app.schemas.query import Source
        sources = []
        for result in results[:top_k]:
            payload = result["payload"]
            sources.append(Source(
                doc_name=payload.get("filename", "Unknown"),
                doc_id=payload.get("doc_id", ""),
                chunk_text=payload.get("content", "")[:200],
                page=payload.get("page_num"),
                score=result["score"]
            ))
        
        # Step 4: Evaluate context
        yield send_event("status", {
            "step": "evaluation",
            "message": "🔬 Evaluating context quality...",
            "timestamp": time.time() - start_time
        })
        
        eval_start = time.time()
        quality = await context_evaluator.score_context(query, sources)
        eval_time = int((time.time() - eval_start) * 1000)
        
        yield send_event("status", {
            "step": "evaluation_done",
            "message": f"✓ Quality: {quality['overall_score']:.2f} - {quality['reason']}",
            "time_ms": eval_time,
            "quality": quality,
            "timestamp": time.time() - start_time
        })
        
        # Step 5: Agent decision
        if quality['is_sufficient']:
            decision = "LOCAL ONLY (sufficient context)"
            mode_used = "local"
        elif current_user.permissions.can_search_internet:
            if quality['overall_score'] < 0.3:
                decision = "INTERNET ONLY (very limited local)"
                mode_used = "internet"
            else:
                decision = "HYBRID (enhance with internet)"
                mode_used = "hybrid"
        else:
            decision = "LOCAL (no internet permission)"
            mode_used = "local"
        
        yield send_event("status", {
            "step": "decision",
            "message": f"🎯 Agent Decision: {decision}",
            "mode": mode_used,
            "timestamp": time.time() - start_time
        })
        
        # Step 6: Generate answer
        if mode_used == "internet" or mode_used == "hybrid":
            yield send_event("status", {
                "step": "internet_search",
                "message": "🌐 Searching internet with Perplexity...",
                "timestamp": time.time() - start_time
            })
            
            internet_start = time.time()
            if mode_used == "internet":
                final_result = await rag_service.query_internet(query, top_k)
            else:
                final_result = await rag_service.query_hybrid(query, top_k, filter_classified)
            internet_time = int((time.time() - internet_start) * 1000)
            
            yield send_event("status", {
                "step": "internet_done",
                "message": f"✓ Internet search complete",
                "time_ms": internet_time,
                "timestamp": time.time() - start_time
            })
        else:
            yield send_event("status", {
                "step": "llm_generate",
                "message": "🤖 Generating answer with Groq LLM...",
                "timestamp": time.time() - start_time
            })
            
            llm_start = time.time()
            final_result = await rag_service.query_local(query, top_k, filter_classified, return_timing=True)
            llm_time = int((time.time() - llm_start) * 1000)
            
            yield send_event("status", {
                "step": "llm_done",
                "message": f"✓ Answer generated",
                "time_ms": llm_time,
                "timestamp": time.time() - start_time
            })
        
        # Step 7: Cache result
        yield send_event("status", {
            "step": "caching",
            "message": "💾 Caching result...",
            "timestamp": time.time() - start_time
        })
        
        await semantic_cache.set(
            query,
            final_result['answer'],
            final_result['sources'],
            final_result['mode'],
            current_user.user_id
        )
        
        total_time = int((time.time() - start_time) * 1000)
        
        yield send_event("status", {
            "step": "complete",
            "message": f"✅ Complete! Total time: {total_time}ms",
            "timestamp": time.time() - start_time
        })
        
        # Send final result (convert Sources to dicts)
        result_data = {
            "answer": final_result['answer'],
            "sources": [
                {
                    "doc_name": s.doc_name,
                    "doc_id": s.doc_id,
                    "chunk_text": s.chunk_text,
                    "page": s.page,
                    "score": s.score,
                    "image_url": s.image_url
                }
                for s in final_result['sources']
            ],
            "mode": final_result['mode'],
            "query": query,
            "query_id": f"stream_{int(time.time())}",
            "processing_time_ms": total_time,
            "context_quality": quality.__dict__ if hasattr(quality, '__dict__') else quality,
            "agent_decision": mode_used
        }
        
        yield send_event("result", result_data)
    
    except Exception as e:
        yield send_event("error", {
            "message": str(e),
            "timestamp": time.time() - start_time
        })


@router.post("/stream")
async def query_stream(
    request: QueryRequest,
    current_user: User = Depends(get_current_user)
):
    """Stream query processing with real-time progress updates"""
    
    # Check permissions
    if request.mode in ["internet", "hybrid"]:
        if not current_user.permissions.can_search_internet:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You don't have permission to use {request.mode} search"
            )
    
    return StreamingResponse(
        stream_agent_query(
            query=request.query,
            mode=request.mode,
            top_k=request.top_k,
            current_user=current_user
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

