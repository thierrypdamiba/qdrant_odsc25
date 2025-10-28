"""Semantic cache for query results"""
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import uuid
from app.services.vector_store import VectorStore
from app.services.document_processor import EmbeddingService
from app.schemas.query import Source


class SemanticCache:
    """Semantic cache using vector similarity for query matching"""
    
    def __init__(
        self,
        vector_store: VectorStore,
        embedding_service: EmbeddingService,
        org_id: str = "default_org",
        similarity_threshold: float = 0.95,
        ttl_hours: int = 24
    ):
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.org_id = org_id
        self.similarity_threshold = similarity_threshold
        self.ttl_hours = ttl_hours
        self.collection_name = f"{org_id}_query_cache"
    
    async def initialize(self):
        """Create cache collection if it doesn't exist"""
        # For cloud inference, we need to create with Document support
        # For regular mode, create with fixed size (384)
        vector_size = None if (hasattr(self.vector_store, 'cloud_inference') and self.vector_store.cloud_inference) else 384
        await self.vector_store.create_collection(self.collection_name, vector_size)
    
    async def get(
        self,
        query: str,
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Check if similar query exists in cache
        
        Returns cached result if similarity > threshold, None otherwise
        """
        try:
            import time
            
            # Determine if we should use cloud inference
            use_cloud = hasattr(self.vector_store, 'cloud_inference') and self.vector_store.cloud_inference
            
            search_start = time.time()
            
            if use_cloud:
                # Cloud inference: send query text directly to Qdrant (no local embedding!)
                print(f"[CACHE GET] Using cloud inference for: {query[:50]}...")
                print(f"[CACHE GET] Cache latency includes:")
                print(f"[CACHE GET]   1. Network send (~30-50ms)")
                print(f"[CACHE GET]   2. Qdrant cloud embedding (~50-100ms)")
                print(f"[CACHE GET]   3. Qdrant vector search (~20-50ms)")
                print(f"[CACHE GET]   4. Network receive (~30-50ms)")
                
                # Track full cloud operation
                cloud_start = time.time()
                results = await self.vector_store.search(
                    collection_name=self.collection_name,
                    query_vector=[],  # Not used
                    top_k=1,
                    filter_conditions={},
                    query_text=query  # Send text, Qdrant embeds it server-side
                )
                cloud_total_time = int((time.time() - cloud_start) * 1000)
                
                print(f"[CACHE GET] Total cloud operation: {cloud_total_time}ms")
                search_time = int((time.time() - search_start) * 1000)
            else:
                # Regular mode: generate embedding locally
                import asyncio
                loop = asyncio.get_event_loop()
                embedding_start = time.time()
                query_vector = await loop.run_in_executor(
                    None,
                    self.embedding_service.embed_text_query,
                    query
                )
                embedding_time = int((time.time() - embedding_start) * 1000)
                print(f"[CACHE GET] Embedding took: {embedding_time}ms")
                
                # Search with the vector
                print(f"[CACHE GET] Searching for query: {query[:50]}...")
                results = await self.vector_store.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    top_k=1,
                    filter_conditions={},
                    query_text=None
                )
                search_time = int((time.time() - search_start) * 1000)
                print(f"[CACHE GET] Total search took: {search_time}ms")
            
            print(f"[CACHE GET] Results: {len(results)} matches found")
            
            if not results:
                print(f"[CACHE GET] No results found for query")
                return None
            
            best_match = results[0]
            
            # Extract timing metadata if available
            qdrant_server_time = best_match.get('_qdrant_time_ms', 0)
            total_cache_time = int((time.time() - search_start) * 1000)
            network_time = total_cache_time - qdrant_server_time if qdrant_server_time > 0 else 0
            
            print(f"[CACHE GET] Best match - ID: {best_match['id']}, Score: {best_match['score']:.4f}, Threshold: {self.similarity_threshold}")
            print(f"[CACHE GET] Cached query: {best_match.get('payload', {}).get('query', 'N/A')[:50]}")
            
            if qdrant_server_time > 0:
                print(f"[CACHE GET] Timing breakdown:")
                print(f"[CACHE GET]   • Qdrant server (embedding + search): {qdrant_server_time:.2f}ms")
                print(f"[CACHE GET]   • Network round-trip: {network_time}ms")
                print(f"[CACHE GET]   • Total: {total_cache_time}ms")
            
            # Check similarity threshold
            if best_match['score'] < self.similarity_threshold:
                print(f"[CACHE GET] Score below threshold: {best_match['score']:.4f} < {self.similarity_threshold}")
                return None
            
            payload = best_match['payload']
            
            # Check TTL
            cached_time = datetime.fromisoformat(payload['timestamp'])
            age = datetime.utcnow() - cached_time
            
            if age > timedelta(hours=self.ttl_hours):
                # Expired
                return None
            
            # Cache hit!
            cache_latency = int((time.time() - search_start) * 1000)
            result_data = {
                "answer": payload['answer'],
                "sources": payload['sources'],
                "mode": payload['mode'],
                "cached": True,
                "cache_score": best_match['score'],
                "cached_query": payload['query'],
                "cache_age_minutes": int(age.total_seconds() / 60),
                "cache_latency_ms": cache_latency,  # Total cache operation time
                "cloud_inference_used": use_cloud
            }
            
            # Add Qdrant server timing if available
            if '_qdrant_time_ms' in best_match:
                result_data['qdrant_server_ms'] = best_match['_qdrant_time_ms']
                result_data['embedding_est_ms'] = best_match.get('_embedding_est_ms', 0)
                result_data['search_est_ms'] = best_match.get('_search_est_ms', 0)
                result_data['network_ms'] = cache_latency - best_match['_qdrant_time_ms']
            
            return result_data
        
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    async def set(
        self,
        query: str,
        answer: str,
        sources: List[Source],
        mode: str,
        user_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """Store query result in cache"""
        try:
            # Prepare payload
            payload = {
                "query": query,
                "answer": answer,
                "sources": [
                    {
                        "doc_name": s.doc_name,
                        "doc_id": s.doc_id,
                        "chunk_text": s.chunk_text,
                        "page": s.page,
                        "score": s.score
                    }
                    for s in sources
                ],
                "mode": mode,
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": user_id or "unknown",
                **(metadata or {})
            }
            
            # Store in cache using cloud inference if available
            cache_id = str(uuid.uuid4())
            use_cloud = hasattr(self.vector_store, 'cloud_inference') and self.vector_store.cloud_inference
            
            print(f"[CACHE SET] use_cloud={use_cloud}, query={query[:50]}...")
            
            if use_cloud:
                # Cloud inference: upload query text, Qdrant embeds it server-side (NO local embedding!)
                print(f"[CACHE SET] Uploading query text to cloud for server-side embedding...")
                await self.vector_store.upsert_vectors(
                    collection_name=self.collection_name,
                    vectors=[[]],  # Empty, Qdrant generates embedding server-side
                    payloads=[payload],
                    ids=[cache_id],
                    texts=[query]  # Qdrant handles embedding
                )
                print(f"[CACHE SET] Successfully cached with cloud inference: {cache_id}")
            else:
                # Regular mode: generate embedding locally
                import asyncio
                loop = asyncio.get_event_loop()
                query_vector = await loop.run_in_executor(
                    None,
                    self.embedding_service.embed_text_query,
                    query
                )
                await self.vector_store.upsert_vectors(
                    collection_name=self.collection_name,
                    vectors=[query_vector],
                    payloads=[payload],
                    ids=[cache_id]
                )
                print(f"[CACHE SET] Successfully cached with local embedding: {cache_id}")
        
        except Exception as e:
            print(f"Cache set error: {e}")
            # Don't fail if cache fails - just log
    
    async def clear_expired(self):
        """Clear expired cache entries (can be run periodically)"""
        # For now, we'll let Qdrant handle this
        # In production, implement a cleanup job
        pass
    
    async def clear_user_cache(self, user_id: str):
        """Clear cache for a specific user"""
        # This would require Qdrant filtering + deletion
        # Simplified for now
        pass

