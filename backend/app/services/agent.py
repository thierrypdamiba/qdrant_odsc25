"""Agentic RAG - Intelligent query routing and decision making"""
from typing import Dict, Any, Optional
from app.services.rag import RAGService
from app.services.context_evaluator import ContextEvaluator
from app.services.semantic_cache import SemanticCache
from app.core.auth import User
from datetime import datetime
import time


class AgenticRAG:
    """
    Intelligent RAG agent that automatically decides:
    - When to search locally vs internet
    - Whether cached results are good enough
    - What combination of sources to use
    """
    
    def __init__(
        self,
        rag_service: RAGService,
        context_evaluator: ContextEvaluator,
        semantic_cache: SemanticCache
    ):
        self.rag = rag_service
        self.evaluator = context_evaluator
        self.cache = semantic_cache
    
    async def query_intelligent(
        self,
        query: str,
        user: User,
        force_mode: Optional[str] = None,
        top_k: int = 5,
        use_mmr: bool = False,
        diversity: float = 0.5
    ) -> Dict[str, Any]:
        """
        Intelligent query processing with automatic routing
        
        Decision tree:
        1. Check semantic cache → return if high similarity
        2. Search local knowledge base
        3. Evaluate context quality
        4. If insufficient → trigger internet search (if permitted)
        5. Generate answer
        6. Cache result
        
        Args:
            query: User's question
            user: Current user (for permissions)
            force_mode: Override agent decision (local/internet/hybrid)
            top_k: Number of sources to retrieve
        
        Returns:
            Query result with agent metadata
        """
        
        start_time = time.time()
        decision_log = []
        perf = {}  # Performance tracking
        
        # Step 1: Check semantic cache
        decision_log.append("🔍 Checking semantic cache...")
        cache_start = time.time()
        cached_result = await self.cache.get(query, user.user_id)
        perf['cache_check_ms'] = int((time.time() - cache_start) * 1000)
        
        if cached_result:
            total_time = int((time.time() - start_time) * 1000)
            decision_log.append(f"⚡ Cache HIT! (similarity: {cached_result['cache_score']:.3f})")
            decision_log.append(f"✓ Returning cached result ({cached_result.get('cache_age_minutes', 0)} min old)")
            
            # Build performance breakdown with cache timing details
            perf_breakdown = {
                "total_ms": total_time,
                "cache_check_ms": perf['cache_check_ms'],
                "embedding_ms": None,
                "qdrant_search_ms": None,
                "context_eval_ms": None,
                "internet_search_ms": None,
                "llm_generation_ms": None,
                "cache_store_ms": None
            }
            
            return {
                **cached_result,
                "query": query,
                "query_id": f"cached_{int(datetime.utcnow().timestamp())}",
                "timestamp": datetime.utcnow(),
                "decision_log": decision_log,
                "processing_time_ms": total_time,
                "performance_breakdown": perf_breakdown
            }
        
        decision_log.append("❌ Cache MISS - processing query...")
        
        # If user forced a specific mode, use it
        if force_mode and force_mode != "auto":
            decision_log.append(f"👤 User forced mode: {force_mode}")
            result = await self._execute_mode(force_mode, query, top_k, user, use_mmr, diversity)
            result['decision_log'] = decision_log
            result['agent_decision'] = f"User override: {force_mode}"
            
            # Cache the result
            cache_start = time.time()
            await self.cache.set(
                query,
                result['answer'],
                result['sources'],
                result['mode'],
                user.user_id,
                {"context_quality": result.get('context_quality')}
            )
            perf['cache_store_ms'] = int((time.time() - cache_start) * 1000)
            
            return result
        
        # Step 2: Search local knowledge base first
        decision_log.append("📚 Searching local knowledge base (Qdrant)...")
        filter_classified = not user.permissions.can_access_classified
        
        local_start = time.time()
        local_result = await self.rag.query_local(
            query,
            top_k,
            filter_classified,
            return_timing=True,
            use_mmr=use_mmr,
            diversity=diversity
        )
        local_total = int((time.time() - local_start) * 1000)
        
        # Extract detailed timings
        if 'timings' in local_result:
            timings = local_result.pop('timings')
            perf['embedding_ms'] = timings.get('embedding_ms', 0)
            perf['qdrant_search_ms'] = timings.get('qdrant_search_ms', 0)
            perf['llm_generation_ms'] = timings.get('llm_generation_ms', 0)
        else:
            perf['qdrant_search_ms'] = local_total
        
        decision_log.append(f"   Found {len(local_result['sources'])} local sources")
        if 'timings' in perf or perf.get('qdrant_search_ms'):
            decision_log.append(f"   → Embedding: {perf.get('embedding_ms', 0)}ms | Qdrant: {perf.get('qdrant_search_ms', 0)}ms | LLM: {perf.get('llm_generation_ms', 0)}ms")
        
        # Step 3: Evaluate context quality
        decision_log.append("🔬 Evaluating context quality...")
        eval_start = time.time()
        quality = await self.evaluator.score_context(query, local_result['sources'])
        perf['context_eval_ms'] = int((time.time() - eval_start) * 1000)
        
        decision_log.append(f"   Quality: {quality['overall_score']:.3f} | Sufficient: {quality['is_sufficient']} (took {perf['context_eval_ms']}ms)")
        decision_log.append(f"   {quality['reason']}")
        
        # Step 4: Intelligent routing decision
        final_result = None
        agent_decision = ""
        
        if quality['is_sufficient']:
            # Local context is good enough
            decision_log.append("✅ Agent Decision: LOCAL ONLY (context sufficient)")
            
            final_result = local_result
            # LLM time was already captured in local_result timings
            agent_decision = "local_sufficient"
        
        elif user.permissions.can_search_internet:
            # Context insufficient but user can access internet
            if quality['overall_score'] < 0.3:
                # Very poor local context - use internet only
                decision_log.append("🌐 Agent Decision: INTERNET ONLY (very limited local data)")
                
                search_start = time.time()
                final_result = await self.rag.query_internet(query, top_k)
                perf['internet_search_ms'] = int((time.time() - search_start) * 1000)
                
                decision_log.append(f"   Internet search completed ({perf['internet_search_ms']}ms)")
                agent_decision = "internet_no_local"
            else:
                # Some local context - combine with internet
                decision_log.append("🔀 Agent Decision: HYBRID (enhancing local with internet)")
                
                search_start = time.time()
                final_result = await self.rag.query_hybrid(query, top_k, filter_classified, use_mmr=use_mmr, diversity=diversity)
                perf['internet_search_ms'] = int((time.time() - search_start) * 1000)
                
                decision_log.append(f"   Hybrid search completed ({perf['internet_search_ms']}ms)")
                agent_decision = "hybrid_partial_local"
        
        else:
            # User cannot access internet - return local even if insufficient
            decision_log.append("⚠️  Agent Decision: LOCAL (insufficient but no internet permission)")
            final_result = local_result
            perf['llm_generation_ms'] = 0
            agent_decision = "local_no_permission"
        
        # Step 5: Add metadata
        total_time = int((time.time() - start_time) * 1000)
        
        final_result['context_quality'] = quality
        final_result['decision_log'] = decision_log
        final_result['agent_decision'] = agent_decision
        final_result['cached'] = False
        final_result['query'] = query
        final_result['query_id'] = f"agent_{int(datetime.utcnow().timestamp())}"
        final_result['timestamp'] = datetime.utcnow()
        final_result['processing_time_ms'] = total_time
        
        # Add performance breakdown
        perf['total_ms'] = total_time
        final_result['performance_breakdown'] = perf
        
        # Step 6: Cache the result
        decision_log.append("💾 Caching result for future queries...")
        cache_start = time.time()
        await self.cache.set(
            query,
            final_result['answer'],
            final_result['sources'],
            final_result['mode'],
            user.user_id,
            {
                "context_quality": quality,
                "agent_decision": agent_decision
            }
        )
        perf['cache_store_ms'] = int((time.time() - cache_start) * 1000)
        
        decision_log.append(f"✓ Complete! Total time: {total_time}ms")
        
        return final_result
    
    async def _execute_mode(
        self,
        mode: str,
        query: str,
        top_k: int,
        user: User,
        use_mmr: bool = False,
        diversity: float = 0.5
    ) -> Dict[str, Any]:
        """Execute a specific mode"""
        filter_classified = not user.permissions.can_access_classified
        
        if mode == "local":
            return await self.rag.query_local(query, top_k, filter_classified, use_mmr=use_mmr, diversity=diversity)
        elif mode == "internet":
            return await self.rag.query_internet(query, top_k)
        elif mode == "hybrid":
            return await self.rag.query_hybrid(query, top_k, filter_classified, use_mmr=use_mmr, diversity=diversity)
        else:
            raise ValueError(f"Unknown mode: {mode}")

