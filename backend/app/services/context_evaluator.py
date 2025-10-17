"""Context quality evaluation for intelligent routing"""
from typing import List, Dict, Any
from app.schemas.query import Source
from app.services.llm import LLMService


class ContextEvaluator:
    """Evaluate if retrieved context is sufficient to answer a query"""
    
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service
    
    async def score_context(
        self,
        query: str,
        sources: List[Source]
    ) -> Dict[str, Any]:
        """
        Score context quality on multiple dimensions
        
        Returns:
            {
                "overall_score": float (0-1),
                "vector_score": float (0-1),
                "coverage": float (0-1),
                "llm_confidence": float (0-1),
                "is_sufficient": bool,
                "reason": str
            }
        """
        
        # No sources = no context
        if not sources or len(sources) == 0:
            return {
                "overall_score": 0.0,
                "vector_score": 0.0,
                "coverage": 0.0,
                "llm_confidence": 0.0,
                "is_sufficient": False,
                "reason": "No relevant documents found in knowledge base"
            }
        
        # 1. Vector similarity score (average of top results)
        vector_score = sum([s.score for s in sources]) / len(sources)
        
        # 2. Query term coverage
        coverage = self._calculate_coverage(query, sources)
        
        # 3. LLM confidence check
        llm_confidence = await self._check_llm_confidence(query, sources)
        
        # Calculate overall score (weighted average)
        overall_score = (
            vector_score * 0.4 +
            coverage * 0.2 +
            llm_confidence * 0.4
        )
        
        # Determine if sufficient
        is_sufficient = overall_score > 0.6 and llm_confidence > 0.5
        
        # Generate reason
        if is_sufficient:
            reason = "Local knowledge base has sufficient information"
        elif overall_score < 0.3:
            reason = "Local knowledge base has very limited information"
        else:
            reason = "Local knowledge base has partial information, internet search recommended"
        
        return {
            "overall_score": round(overall_score, 3),
            "vector_score": round(vector_score, 3),
            "coverage": round(coverage, 3),
            "llm_confidence": round(llm_confidence, 3),
            "is_sufficient": is_sufficient,
            "reason": reason
        }
    
    def _calculate_coverage(self, query: str, sources: List[Source]) -> float:
        """Calculate what % of query terms appear in retrieved context"""
        query_terms = set(query.lower().split())
        
        # Remove common stop words
        stop_words = {'what', 'is', 'the', 'a', 'an', 'how', 'why', 'when', 'where', 'who', 'tell', 'me', 'about'}
        query_terms = query_terms - stop_words
        
        if not query_terms:
            return 0.5  # Default if only stop words
        
        # Combine all source text
        context_text = " ".join([s.chunk_text.lower() for s in sources])
        context_words = set(context_text.split())
        
        # Calculate coverage
        matched = len(query_terms & context_words)
        coverage = matched / len(query_terms)
        
        return min(coverage, 1.0)
    
    async def _check_llm_confidence(self, query: str, sources: List[Source]) -> float:
        """Use LLM to judge if context can answer the query"""
        
        # Combine context
        context_text = "\n\n".join([
            f"[Source {i+1}] {s.chunk_text[:300]}"
            for i, s in enumerate(sources[:3])
        ])
        
        # Ask LLM to evaluate
        system_prompt = """You are a context evaluator. Your job is to determine if the provided context contains enough information to answer the user's question.

Respond with ONLY a number between 0 and 1:
- 1.0 = Context fully answers the question
- 0.7-0.9 = Context mostly answers the question
- 0.4-0.6 = Context partially answers the question
- 0.1-0.3 = Context barely relevant
- 0.0 = Context cannot answer the question

Only respond with a single number."""
        
        user_prompt = f"""Question: {query}

Context:
{context_text}

Confidence score (0-1):"""
        
        try:
            response = await self.llm_service.generate(user_prompt, system_prompt)
            
            # Extract number from response
            response_clean = response.strip()
            
            # Try to parse as float
            try:
                score = float(response_clean.split()[0])
                return max(0.0, min(1.0, score))  # Clamp between 0 and 1
            except:
                # If parsing fails, use heuristic based on response
                if "cannot" in response_clean.lower() or "no" in response_clean.lower():
                    return 0.2
                elif "fully" in response_clean.lower() or "yes" in response_clean.lower():
                    return 0.9
                else:
                    return 0.5
        
        except Exception as e:
            print(f"LLM confidence check error: {e}")
            # Fallback to average vector score
            if sources:
                avg_score = sum([s.score for s in sources]) / len(sources)
                return avg_score
            return 0.0

