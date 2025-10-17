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
        await self.vector_store.create_collection(self.collection_name, 384)
    
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
            # Generate query embedding
            query_vector = self.embedding_service.embed_text_query(query)
            
            # Search cache for similar queries
            results = await self.vector_store.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                top_k=1,
                filter_conditions={}  # Could filter by user_id if needed
            )
            
            if not results:
                return None
            
            best_match = results[0]
            
            # Check similarity threshold
            if best_match['score'] < self.similarity_threshold:
                return None
            
            payload = best_match['payload']
            
            # Check TTL
            cached_time = datetime.fromisoformat(payload['timestamp'])
            age = datetime.utcnow() - cached_time
            
            if age > timedelta(hours=self.ttl_hours):
                # Expired
                return None
            
            # Cache hit!
            return {
                "answer": payload['answer'],
                "sources": payload['sources'],
                "mode": payload['mode'],
                "cached": True,
                "cache_score": best_match['score'],
                "cached_query": payload['query'],
                "cache_age_minutes": int(age.total_seconds() / 60)
            }
        
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
            # Generate query embedding
            query_vector = self.embedding_service.embed_text_query(query)
            
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
            
            # Store in cache
            cache_id = str(uuid.uuid4())
            await self.vector_store.upsert_vectors(
                collection_name=self.collection_name,
                vectors=[query_vector],
                payloads=[payload],
                ids=[cache_id]
            )
        
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

