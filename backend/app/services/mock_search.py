"""Mock search service implementation for testing without API keys"""
from typing import List, Dict
from app.services.search import SearchService


class MockSearchService(SearchService):
    """Mock search service that returns simulated internet search results"""
    
    async def search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """Return mock search results"""
        # Simulate internet search with mock data
        mock_results = []
        for i in range(min(num_results, 3)):  # Return up to 3 mock results
            mock_results.append({
                "title": f"Mock Search Result {i+1}",
                "url": f"https://example.com/result{i+1}",
                "snippet": f"This is a mock search result for '{query}'. In a real scenario, this would contain actual internet search results. The Perplexity API is not configured, so using mock data for demonstration.",
                "score": 0.95 - (i * 0.1)
            })
        
        return mock_results

