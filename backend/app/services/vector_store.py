"""Qdrant vector store implementation"""
from typing import List, Dict, Any, Optional
import uuid
import time
from abc import ABC, abstractmethod


class VectorStore(ABC):
    """Abstract base class for vector stores"""
    
    @abstractmethod
    async def create_collection(self, collection_name: str, vector_size: Optional[int] = None):
        """Create a new collection"""
        pass
    
    @abstractmethod
    async def upsert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
        texts: Optional[List[str]] = None
    ):
        """Insert or update vectors"""
        pass
    
    @abstractmethod
    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 5,
        filter_conditions: Optional[Dict[str, Any]] = None,
        query_text: Optional[str] = None,
        use_mmr: bool = False,
        diversity: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
        pass
    
    @abstractmethod
    async def delete(self, collection_name: str, ids: List[str]):
        """Delete vectors by ID"""
        pass
    
    @abstractmethod
    async def get_by_id(self, collection_name: str, point_id: str) -> Optional[Dict[str, Any]]:
        """Get a vector by ID"""
        pass


class QdrantVectorStore(VectorStore):
    """Qdrant cloud vector store implementation"""
    
    def __init__(self, url: str, api_key: Optional[str] = None, cloud_inference: bool = False):
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams
        
        # cloud_inference parameter doesn't exist - it's determined by the vector format
        self.client = QdrantClient(url=url, api_key=api_key)
        self.api_key = api_key  # Store for REST API calls
        self.cloud_inference = cloud_inference
        self.Distance = Distance
        self.VectorParams = VectorParams
    
    async def create_collection(self, collection_name: str, vector_size: Optional[int] = None):
        """Create a new collection"""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            
            if self.cloud_inference and vector_size is None:
                # For cloud inference with Document-based queries, still need vector config
                await loop.run_in_executor(
                    None,
                    lambda: self.client.create_collection(
                        collection_name=collection_name,
                        vectors_config=self.VectorParams(
                            size=384,
                            distance=self.Distance.COSINE
                        )
                    )
                )
            else:
                # For regular mode, specify the vector size
                await loop.run_in_executor(
                    None,
                    lambda: self.client.create_collection(
                        collection_name=collection_name,
                        vectors_config=self.VectorParams(
                            size=vector_size or 384,
                            distance=self.Distance.COSINE
                        )
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
        ids: Optional[List[str]] = None,
        texts: Optional[List[str]] = None
    ):
        """Insert or update vectors"""
        import asyncio
        import httpx
        
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in vectors]
        
        # If cloud inference and texts provided, use REST API for cloud embedding
        if self.cloud_inference and texts:
            # Use REST API directly for cloud inference
            url = f"{self.client._client.rest_uri}/collections/{collection_name}/points?wait=true"
            headers = {
                "Content-Type": "application/json",
                "api-key": self.api_key or ""
            }
            
            points_data = [
                {
                    "id": point_id,
                    "payload": payload,
                    "vector": {
                        "text": text,
                        "model": "sentence-transformers/all-minilm-l6-v2"
                    }
                }
                for point_id, text, payload in zip(ids, texts, payloads)
            ]
            
            data = {"points": points_data}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.put(url, json=data, headers=headers)
                if response.status_code not in [200, 201]:
                    print(f"[VECTOR_STORE] Cloud upsert failed: {response.status_code} - {response.text}")
                    raise Exception(f"Qdrant upsert failed: {response.status_code} - {response.text}")
                print(f"[VECTOR_STORE] Successfully uploaded {len(points_data)} points with cloud inference")
        else:
            # Regular mode: use Python client with pre-computed vectors
            from qdrant_client.models import PointStruct
            
            points = [
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload
                )
                for point_id, vector, payload in zip(ids, vectors, payloads)
            ]
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.upsert(
                    collection_name=collection_name,
                    points=points
                )
            )
    
    async def search(
        self,
        collection_name: str,
        query_vector: List[float],
        top_k: int = 5,
        filter_conditions: Optional[Dict[str, Any]] = None,
        query_text: Optional[str] = None,
        use_mmr: bool = False,
        diversity: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Search for similar vectors"""
        import asyncio
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        
        search_filter = None
        if filter_conditions:
            conditions = [
                FieldCondition(key=key, match=MatchValue(value=value))
                for key, value in filter_conditions.items()
            ]
            search_filter = Filter(must=conditions)
        
        # If cloud inference and query_text provided, use REST API for cloud embedding
        if self.cloud_inference and query_text:
            import httpx
            
            # Use REST API directly for cloud inference
            url = f"{self.client._client.rest_uri}/collections/{collection_name}/points/query"
            headers = {
                "Content-Type": "application/json",
                "api-key": self.api_key or ""
            }
            
            data = {
                "query": {
                    "text": query_text,
                    "model": "sentence-transformers/all-minilm-l6-v2"
                },
                "limit": top_k,
                "with_payload": True
            }
            
            print(f"[VECTOR_STORE] Cloud query URL: {url}")
            print(f"[VECTOR_STORE] Query text: {query_text[:50]}...")
            
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                network_start = time.time()
                response = await http_client.post(url, json=data, headers=headers)
                total_call_time = (time.time() - network_start) * 1000
                
                print(f"[VECTOR_STORE] Response status: {response.status_code}")
                
                if response.status_code != 200:
                    print(f"[VECTOR_STORE] Cloud query failed: {response.status_code} - {response.text}")
                    raise Exception(f"Qdrant query failed: {response.status_code} - {response.text}")
                
                result = response.json()
                points = result.get("result", {}).get("points", [])
                qdrant_server_time = result.get("time", 0) * 1000  # Qdrant's reported server time
                network_time = total_call_time - qdrant_server_time
                usage = result.get("usage", {})
                
                # Estimate embedding vs search time based on typical ratios
                # Embedding typically takes 60-70% of Qdrant server time
                estimated_embedding_time = qdrant_server_time * 0.65
                estimated_search_time = qdrant_server_time * 0.35
                
                print(f"[VECTOR_STORE] Cloud query returned {len(points)} results")
                print(f"[VECTOR_STORE] Timing breakdown:")
                print(f"[VECTOR_STORE]   • Total call: {total_call_time:.2f}ms")
                print(f"[VECTOR_STORE]   • Qdrant server: {qdrant_server_time:.2f}ms")
                print(f"[VECTOR_STORE]     ├─ Embedding (est): {estimated_embedding_time:.2f}ms")
                print(f"[VECTOR_STORE]     └─ Search (est): {estimated_search_time:.2f}ms")
                print(f"[VECTOR_STORE]   • Network: {network_time:.2f}ms")
                if usage:
                    print(f"[VECTOR_STORE] Inference usage: {usage}")
                
                if points:
                    print(f"[VECTOR_STORE] First result score: {points[0].get('score')}")
                
                # Return results with timing metadata
                results_list = [
                    {
                        "id": str(hit["id"]),
                        "score": hit["score"],
                        "payload": hit.get("payload", {})
                    }
                    for hit in points
                ]
                
                # Attach timing metadata to first result if exists
                if results_list:
                    results_list[0]["_qdrant_time_ms"] = qdrant_server_time
                    results_list[0]["_embedding_est_ms"] = estimated_embedding_time
                    results_list[0]["_search_est_ms"] = estimated_search_time
                    results_list[0]["_network_ms"] = network_time
                    results_list[0]["_usage"] = usage
                
                return results_list
        else:
            # Use MMR if requested
            if use_mmr:
                from qdrant_client import models
                loop = asyncio.get_event_loop()
                results = await loop.run_in_executor(
                    None,
                    lambda: self.client.query_points(
                        collection_name=collection_name,
                        query=models.Query(
                            nearest=models.Nearest(
                                vector=query_vector
                            ),
                            mmr=models.Mmr(
                                diversity=diversity,  # 0.0 = relevance, 1.0 = diversity
                                candidates_limit=min(100, top_k * 10)  # get more candidates for diversity
                            )
                        ),
                        limit=top_k,
                        query_filter=search_filter
                    )
                )
            else:
                # Traditional vector search
                loop = asyncio.get_event_loop()
                results = await loop.run_in_executor(
                    None,
                    lambda: self.client.search(
                        collection_name=collection_name,
                        query_vector=query_vector,
                        limit=top_k,
                        query_filter=search_filter
                    )
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
        import asyncio
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.client.delete(
                collection_name=collection_name,
                points_selector=ids
            )
        )
    
    async def get_by_id(self, collection_name: str, point_id: str) -> Optional[Dict[str, Any]]:
        """Get a vector by ID"""
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            lambda: self.client.retrieve(
                collection_name=collection_name,
                ids=[point_id]
            )
        )
        
        if result:
            point = result[0]
            return {
                "id": str(point.id),
                "payload": point.payload,
                "vector": point.vector
            }
        return None


