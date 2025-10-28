"""RAG pipeline orchestration"""
from typing import List, Dict, Any, Optional
from app.services.vector_store import VectorStore
from app.services.llm import LLMService
from app.services.search import SearchService
from app.services.document_processor import EmbeddingService
from app.schemas.query import Source
import uuid
from datetime import datetime


class RAGService:
    """Orchestrate RAG pipeline - retrieval and generation"""
    
    def __init__(
        self,
        vector_store: VectorStore,
        llm_service: LLMService,
        search_service: SearchService,
        embedding_service: EmbeddingService,
        org_id: str = "default_org"
    ):
        self.vector_store = vector_store
        self.llm_service = llm_service
        self.search_service = search_service
        self.embedding_service = embedding_service
        self.org_id = org_id
    
    async def query_local(
        self,
        query: str,
        top_k: int = 5,
        filter_classified: bool = True,
        return_timing: bool = False,
        use_mmr: bool = False,
        diversity: float = 0.5
    ) -> Dict[str, Any]:
        """Query local knowledge base using RAG"""
        import time
        timings = {}
        
        collection_name = f"{self.org_id}_text"
        
        # Check if using cloud inference
        use_cloud = hasattr(self.vector_store, 'cloud_inference') and self.vector_store.cloud_inference
        
        if use_cloud:
            # Cloud inference: Qdrant generates embeddings server-side
            # No local embedding needed!
            print(f"[RAG] Using cloud inference - sending query text to Qdrant")
            query_vector = []  # Not used
            timings['embedding_ms'] = 0  # No local embedding time
        else:
            # Generate query embedding locally
            import asyncio
            embed_start = time.time()
            loop = asyncio.get_event_loop()
            query_vector = await loop.run_in_executor(
                None,
                self.embedding_service.embed_text_query,
                query
            )
            timings['embedding_ms'] = int((time.time() - embed_start) * 1000)
        
        # Apply filters
        filter_conditions = {}
        if filter_classified:
            # This will exclude documents with "classified" tag
            # Note: This is a simplified approach. In production, you'd use Qdrant's filter syntax
            pass
        
        search_start = time.time()
        results = await self.vector_store.search(
            collection_name=collection_name,
            query_vector=query_vector,
            top_k=top_k,
            filter_conditions=filter_conditions,
            use_mmr=use_mmr,
            diversity=diversity,
            query_text=query if use_cloud else None  # Pass text for cloud inference
        )
        timings['qdrant_search_ms'] = int((time.time() - search_start) * 1000)
        
        # Filter out classified documents if needed
        if filter_classified:
            results = [
                r for r in results
                if "classified" not in r["payload"].get("tags", [])
            ]
        
        # Assemble context from retrieved chunks
        context_parts = []
        sources = []
        
        for i, result in enumerate(results[:top_k]):
            payload = result["payload"]
            chunk_text = payload.get("content", "")
            context_parts.append(f"[Source {i+1}] {chunk_text}")
            
            sources.append(Source(
                doc_name=payload.get("filename", "Unknown"),
                doc_id=payload.get("doc_id", ""),
                chunk_text=chunk_text[:200],
                page=payload.get("page_num"),
                score=result["score"]
            ))
        
        context = "\n\n".join(context_parts)
        
        # Generate response
        system_prompt = """You are a helpful AI assistant. Answer the user's question based on the provided context.
If the context doesn't contain enough information to answer the question, say so clearly.
Always cite your sources by mentioning [Source N] when using information from the context."""
        
        user_prompt = f"""Context:
{context}

User Question: {query}

Please provide a comprehensive answer based on the context above."""
        
        llm_start = time.time()
        answer = await self.llm_service.generate(user_prompt, system_prompt)
        timings['llm_generation_ms'] = int((time.time() - llm_start) * 1000)
        
        result = {
            "answer": answer,
            "sources": sources,
            "mode": "local"
        }
        
        if return_timing:
            result['timings'] = timings
        
        return result
    
    async def query_internet(self, query: str, num_results: int = 5) -> Dict[str, Any]:
        """Query internet using search service"""
        # Search the internet
        search_results = await self.search_service.search(query, num_results)
        
        # Assemble context from search results
        context_parts = []
        sources = []
        
        for i, result in enumerate(search_results):
            snippet = result.get("snippet", "")
            context_parts.append(f"[Source {i+1}] {snippet}")
            
            sources.append(Source(
                doc_name=result.get("title", "Internet Source"),
                doc_id=result.get("url", ""),
                chunk_text=snippet[:200],
                score=result.get("score", 0.0)
            ))
        
        context = "\n\n".join(context_parts)
        
        # Generate response
        system_prompt = """You are a helpful AI assistant with access to internet search results.
Answer the user's question based on the provided search results.
Always cite your sources by mentioning [Source N] when using information."""
        
        user_prompt = f"""Search Results:
{context}

User Question: {query}

Please provide a comprehensive answer based on the search results above."""
        
        answer = await self.llm_service.generate(user_prompt, system_prompt)
        
        return {
            "answer": answer,
            "sources": sources,
            "mode": "internet"
        }
    
    async def query_hybrid(
        self,
        query: str,
        top_k: int = 5,
        filter_classified: bool = True,
        use_mmr: bool = False,
        diversity: float = 0.5
    ) -> Dict[str, Any]:
        """Query both local and internet, then fuse results"""
        # Run both queries in parallel (simplified - not truly parallel here)
        local_result = await self.query_local(query, top_k, filter_classified, use_mmr=use_mmr, diversity=diversity)
        internet_result = await self.query_internet(query, top_k)
        
        # Combine sources
        all_sources = local_result["sources"] + internet_result["sources"]
        
        # Combine contexts for final synthesis
        combined_context = f"""Local Knowledge Base Information:
{local_result['answer']}

Internet Search Information:
{internet_result['answer']}"""
        
        system_prompt = """You are a helpful AI assistant with access to both internal documents and internet information.
Synthesize information from both sources to provide a comprehensive answer.
If there are conflicts, note them. Indicate which information comes from internal docs vs. internet."""
        
        user_prompt = f"""{combined_context}

User Question: {query}

Please provide a comprehensive answer that synthesizes both sources of information."""
        
        final_answer = await self.llm_service.generate(user_prompt, system_prompt)
        
        return {
            "answer": final_answer,
            "sources": all_sources,
            "mode": "hybrid"
        }
    
    def _detect_intent(self, query: str) -> str:
        """Detect if query needs real-time info (simple keyword-based)"""
        realtime_keywords = [
            "latest", "recent", "current", "today", "now",
            "2024", "2025", "this year", "this month"
        ]
        
        query_lower = query.lower()
        for keyword in realtime_keywords:
            if keyword in query_lower:
                return "internet"
        
        return "local"


