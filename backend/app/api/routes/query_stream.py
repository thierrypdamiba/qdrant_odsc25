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

# Initialize services once at module level (reused across requests)
_services_initialized = False
_vector_store = None
_llm_service = None
_search_service = None
_embedding_service = None
_rag_service = None
_context_evaluator = None
_semantic_cache = None

async def get_services():
    """Get or initialize services (singleton pattern)"""
    global _services_initialized, _vector_store, _llm_service, _search_service
    global _embedding_service, _rag_service, _context_evaluator, _semantic_cache
    
    if not _services_initialized:
        _vector_store = QdrantVectorStore(
            settings.qdrant_url, 
            settings.qdrant_api_key,
            cloud_inference=settings.qdrant_cloud_inference
        )
        _llm_service = GroqLLMService(settings.groq_api_key)
        _search_service = PerplexitySearchService(settings.perplexity_api_key)
        
        _embedding_service = EmbeddingService(settings.text_embedding_model)
        
        _rag_service = RAGService(
            vector_store=_vector_store,
            llm_service=_llm_service,
            search_service=_search_service,
            embedding_service=_embedding_service,
            org_id=settings.org_id
        )
        
        _context_evaluator = ContextEvaluator(_llm_service)
        _semantic_cache = SemanticCache(
            vector_store=_vector_store,
            embedding_service=_embedding_service,
            org_id=settings.org_id
        )
        await _semantic_cache.initialize()
        
        _services_initialized = True
    
    return {
        'vector_store': _vector_store,
        'llm_service': _llm_service,
        'search_service': _search_service,
        'embedding_service': _embedding_service,
        'rag_service': _rag_service,
        'context_evaluator': _context_evaluator,
        'semantic_cache': _semantic_cache
    }


def _get_suggested_modes(quality, user):
    """Get suggested search modes based on quality and permissions"""
    suggestions = []
    
    if user.permissions.can_search_internet:
        if quality['overall_score'] < 0.3:
            suggestions.append({
                "mode": "internet",
                "reason": "Very limited local context - recommend internet search"
            })
        elif quality['overall_score'] < 0.6:
            suggestions.append({
                "mode": "hybrid",
                "reason": "Some local context - recommend hybrid search"
            })
            suggestions.append({
                "mode": "internet",
                "reason": "Or use internet only for broader coverage"
            })
    
    suggestions.append({
        "mode": "local",
        "reason": "Use local context only"
    })
    
    return suggestions


async def stream_agent_query(
    query: str,
    mode: str,
    top_k: int,
    current_user: User,
    use_mmr: bool = False,
    diversity: float = 0.5
):
    """Stream query processing steps in real-time"""
    
    def send_event(event_type: str, data: dict):
        """Helper to format SSE events"""
        return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
    
    try:
        # Get initialized services (reused across requests)
        init_start = time.time()
        services = await get_services()
        vector_store = services['vector_store']
        llm_service = services['llm_service']
        search_service = services['search_service']
        embedding_service = services['embedding_service']
        rag_service = services['rag_service']
        context_evaluator = services['context_evaluator']
        semantic_cache = services['semantic_cache']
        init_time = int((time.time() - init_start) * 1000)
        
        # Start timing AFTER initialization
        start_time = time.time()
        
        # Step 1: Check cache
        cache_msg = "🔍 Checking semantic cache (cloud inference - no local embedding)..." if settings.qdrant_cloud_inference else "🔍 Checking semantic cache (embedding query & searching for similar cached queries)..."
        yield send_event("status", {
            "step": "cache_check",
            "message": cache_msg,
            "timestamp": time.time() - start_time
        })
        
        cache_start = time.time()
        cached_result = await semantic_cache.get(query, current_user.user_id)
        cache_time = int((time.time() - cache_start) * 1000)
        
        if cached_result:
            # Show breakdown for cloud inference with actual measurements
            if settings.qdrant_cloud_inference and 'cache_latency_ms' in cached_result:
                qdrant_server_ms = cached_result.get('_qdrant_server_ms', 0)
                cache_latency = cached_result.get('cache_latency_ms', cache_time)
                network_ms = cache_latency - qdrant_server_ms if qdrant_server_ms > 0 else 0
                
                cache_msg = f"⚡ CACHE HIT! (similarity: {cached_result['cache_score']:.3f})"
                
                yield send_event("status", {
                    "step": "cache_hit",
                    "message": cache_msg,
                    "time_ms": cache_time,
                    "timestamp": time.time() - start_time
                })
                
                # Show actual measured breakdown
                if qdrant_server_ms > 0:
                    yield send_event("status", {
                        "step": "cache_breakdown",
                        "message": f"   └─ Total: {cache_latency}ms breakdown:",
                        "timestamp": time.time() - start_time
                    })
                    
                    yield send_event("status", {
                        "step": "cache_qdrant",
                        "message": f"      • Qdrant server (embedding + search): {qdrant_server_ms:.2f}ms",
                        "timestamp": time.time() - start_time
                    })
                    
                    yield send_event("status", {
                        "step": "cache_network",
                        "message": f"      • Network round-trip: {network_ms}ms",
                        "timestamp": time.time() - start_time
                    })
                else:
                    yield send_event("status", {
                        "step": "cache_breakdown",
                        "message": f"   └─ Total: {cache_latency}ms (network + cloud embedding + search)",
                        "timestamp": time.time() - start_time
                    })
            else:
                cache_msg = f"⚡ CACHE HIT! (similarity: {cached_result['cache_score']:.3f}, took {cache_time}ms)"
                yield send_event("status", {
                    "step": "cache_hit",
                    "message": cache_msg,
                    "time_ms": cache_time,
                    "timestamp": time.time() - start_time
                })
            
            # Calculate actual processing time (cache lookup only)
            actual_processing_time = int((time.time() - start_time) * 1000)
            
            yield send_event("result", {
                **cached_result,
                "processing_time_ms": actual_processing_time,
                "cache_only_ms": cache_time,  # Pure cache time
                "overhead_ms": actual_processing_time - cache_time  # SSE/serialization overhead
            })
            return
        
        yield send_event("status", {
            "step": "cache_miss",
            "message": f"❌ Cache MISS - no similar query found (took {cache_time}ms)",
            "time_ms": cache_time,
            "timestamp": time.time() - start_time
        })
        
        # Step 2: Search Qdrant (with cloud inference if enabled)
        if settings.qdrant_cloud_inference:
            yield send_event("status", {
                "step": "qdrant_search",
                "message": "📚 Searching knowledge base (cloud inference - Qdrant embeds & searches)...",
                "timestamp": time.time() - start_time
            })
        else:
            yield send_event("status", {
                "step": "embedding",
                "message": "🔤 Generating query embedding...",
                "timestamp": time.time() - start_time
            })
        
        search_start = time.time()
        filter_classified = not current_user.permissions.can_access_classified
        collection_name = f"{settings.org_id}_text"
        
        if settings.qdrant_cloud_inference:
            # Cloud inference: no local embedding needed
            results = await vector_store.search(
                collection_name=collection_name,
                query_vector=[],  # Not used
                top_k=top_k,
                filter_conditions={},
                query_text=query,  # Qdrant handles embedding
                use_mmr=use_mmr,
                diversity=diversity
            )
            search_time = int((time.time() - search_start) * 1000)
            
            yield send_event("status", {
                "step": "qdrant_done",
                "message": f"✓ Found {len(results)} sources (cloud: {search_time}ms)",
                "time_ms": search_time,
                "num_sources": len(results),
                "timestamp": time.time() - start_time
            })
        else:
            # Local embedding + search
            import asyncio
            loop = asyncio.get_event_loop()
            embed_start = time.time()
            query_vector = await loop.run_in_executor(
                None,
                embedding_service.embed_text_query,
                query
            )
            embed_time = int((time.time() - embed_start) * 1000)
            
            yield send_event("status", {
                "step": "embedding_done",
                "message": f"✓ Query embedded ({embed_time}ms)",
                "time_ms": embed_time,
                "timestamp": time.time() - start_time
            })
            
            yield send_event("status", {
                "step": "qdrant_search",
                "message": "📚 Searching Qdrant vector database...",
                "timestamp": time.time() - start_time
            })
            
            results = await vector_store.search(
                collection_name=collection_name,
                query_vector=query_vector,
                top_k=top_k,
                use_mmr=use_mmr,
                diversity=diversity
            )
            search_time = int((time.time() - search_start) * 1000)
            
            yield send_event("status", {
                "step": "qdrant_done",
                "message": f"✓ Found {len(results)} sources from Qdrant",
                "time_ms": search_time,
                "num_sources": len(results),
                "timestamp": time.time() - start_time
            })
        
        if filter_classified:
            results = [r for r in results if "classified" not in r["payload"].get("tags", [])]
        
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
        
        # Step 3: Evaluate context
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
        
        # Step 4: Agent decision with human-in-the-loop fallback
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
        
        # Send decision with quality context for human-in-the-loop
        yield send_event("decision", {
            "step": "decision",
            "message": f"🎯 Agent Decision: {decision}",
            "mode": mode_used,
            "quality_score": quality['overall_score'],
            "quality_reason": quality['reason'],
            "suggested_modes": _get_suggested_modes(quality, current_user),
            "timestamp": time.time() - start_time
        })
        
        # Step 5: Generate answer
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
        
        # Step 6: Cache result
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
            current_user=current_user,
            use_mmr=request.use_mmr,
            diversity=request.diversity
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

