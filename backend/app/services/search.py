"""Perplexity internet search service implementation"""
from typing import List, Dict
from abc import ABC, abstractmethod


class SearchService(ABC):
    """Abstract base class for search services"""
    
    @abstractmethod
    async def search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """Search for information"""
        pass


class PerplexitySearchService(SearchService):
    """Perplexity search service implementation using HTTP API"""
    
    def __init__(self, api_key: str):
        import httpx
        self.api_key = api_key
        self.base_url = "https://api.perplexity.ai"
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """Search using Perplexity API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        payload = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "system",
                    "content": "Be precise and concise. Provide relevant sources when available."
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "max_tokens": 1024,
            "temperature": 0.2
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            response.raise_for_status()
            
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            
            # Perplexity returns the answer - wrap as search result
            results = [{
                "title": "Perplexity AI - Real-time Search",
                "url": "https://www.perplexity.ai",
                "snippet": content,
                "score": 0.95
            }]
            
            return results
        
        except Exception as e:
            import traceback
            print(f"Perplexity search error: {e}")
            print(f"Error details: {traceback.format_exc()}")
            raise Exception(f"Search failed: {e}")


