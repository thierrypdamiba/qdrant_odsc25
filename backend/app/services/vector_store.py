"""Qdrant vector store implementation"""
from typing import List, Dict, Any, Optional
import uuid


class QdrantVectorStore:
    """Qdrant cloud vector store implementation"""
    
    def __init__(self, url: str, api_key: Optional[str] = None):
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams
        
        self.client = QdrantClient(url=url, api_key=api_key)
        self.Distance = Distance
        self.VectorParams = VectorParams
    
    async def create_collection(self, collection_name: str, vector_size: int):
        """Create a new collection"""
        try:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=self.VectorParams(
                    size=vector_size,
                    distance=self.Distance.COSINE
                )
            )
        except Exception as e:
            # Collection might already exist
            print(f"Collection creation: {e}")
    
    async def upsert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ):
        """Insert or update vectors"""
        from qdrant_client.models import PointStruct
        
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in vectors]
        
        points = [
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
            for point_id, vector, payload in zip(ids, vectors, payloads)
        ]
        
        self.client.upsert(
            collection_name=collection_name,
            points=points
        )
    
    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 5,
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        search_filter = None
        if filter_conditions:
            conditions = [
                FieldCondition(key=key, match=MatchValue(value=value))
                for key, value in filter_conditions.items()
            ]
            search_filter = Filter(must=conditions)
        
        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
            query_filter=search_filter
        )
        
        return [
            {
                "id": str(hit.id),
                "score": hit.score,
                "payload": hit.payload
            }
            for hit in results
        ]
    
    async def delete(self, collection_name: str, ids: List[str]):
        """Delete vectors by ID"""
        self.client.delete(
            collection_name=collection_name,
            points_selector=ids
        )
    
    async def get_by_id(self, collection_name: str, point_id: str) -> Optional[Dict[str, Any]]:
        """Get a vector by ID"""
        result = self.client.retrieve(
            collection_name=collection_name,
            ids=[point_id]
        )
        
        if result:
            point = result[0]
            return {
                "id": str(point.id),
                "payload": point.payload,
                "vector": point.vector
            }
        return None


