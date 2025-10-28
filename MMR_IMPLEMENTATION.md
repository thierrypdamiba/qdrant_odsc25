# MMR (Maximal Marginal Relevance) Implementation

## Overview

This implementation adds a toggle to let users get more diverse results using MMR (Maximal Marginal Relevance), which balances relevance with diversity in search results.

## What is MMR?

MMR balances relevance with diversity:
- **diversity = 0.0**: Maximum relevance to the query (traditional similarity search)
- **diversity = 0.5**: Balanced approach between relevance and diversity
- **diversity = 1.0**: Maximum diversity, less emphasis on exact relevance

## Implementation Details

### Backend Changes

1. **Vector Store (`backend/app/services/vector_store.py`)**
   - Added `use_mmr` and `diversity` parameters to the `search` method
   - Implemented Qdrant MMR query with configurable diversity
   - When `use_mmr=True`, uses Qdrant's `query_points` with MMR configuration

2. **RAG Service (`backend/app/services/rag.py`)**
   - Added `use_mmr` and `diversity` parameters to `query_local` and `query_hybrid`
   - Passes these parameters through to the vector store

3. **Agent Service (`backend/app/services/agent.py`)**
   - Added `use_mmr` and `diversity` parameters to `query_intelligent` method
   - Passes parameters through to RAG service methods

4. **API Routes**
   - `backend/app/api/routes/query.py`: Updated to accept MMR parameters
   - `backend/app/api/routes/query_stream.py`: Updated streaming endpoint to support MMR

5. **Schemas (`backend/app/schemas/query.py`)**
   - Added `use_mmr: bool = False` and `diversity: float = 0.5` to `QueryRequest`

### Frontend Changes

1. **API Client (`frontend/lib/api.ts`)**
   - Updated `QueryRequest` interface to include `use_mmr` and `diversity` fields

2. **Query Page (`frontend/app/query/page.tsx`)**
   - Added toggle checkbox to enable/disable MMR
   - Added slider to control diversity level (0.0 to 1.0)
   - Shows helpful description of MMR and diversity levels

3. **Streaming Query Component (`frontend/components/StreamingQuery.tsx`)**
   - Added same MMR toggle and diversity slider
   - Integrated with streaming query functionality

## Usage

### Enable Diversity Search

1. Open the Query page or Streaming Query page
2. Check the "🎨 Enable Diversity Search (MMR)" checkbox
3. Adjust the diversity level using the slider:
   - 0.0 = Relevance only (traditional search)
   - 0.5 = Balanced (default)
   - 1.0 = Maximum diversity
4. Submit your query

### How It Works

When MMR is enabled:
- The backend uses Qdrant's MMR query instead of traditional similarity search
- The algorithm selects results that are:
  - Relevant to the query (vector similarity)
  - Diverse from each other (marginal relevance)
- The `diversity` parameter controls the balance between these two factors

### Example Use Cases

**Lower diversity (0.0-0.3)**: Best for finding the most relevant information
- "What is machine learning?" → Gets most similar content
- Good for factual queries

**Medium diversity (0.4-0.6)**: Balanced results
- "Tell me about renewable energy" → Mix of different aspects
- Good for exploratory queries

**Higher diversity (0.7-1.0)**: Broad coverage
- "Research project ideas" → Wide variety of different topics
- Good for brainstorming and discovery

## Technical Implementation

### Qdrant MMR Configuration

```python
results = await vector_store.search(
    collection_name=collection_name,
    query_vector=query_vector,
    top_k=top_k,
    use_mmr=True,
    diversity=0.5
)
```

Under the hood, this uses Qdrant's MMR query:

```python
query=models.Query(
    nearest=models.Nearest(vector=query_vector),
    mmr=models.Mmr(
        diversity=diversity,  # 0.0 = relevance, 1.0 = diversity
        candidates_limit=min(100, top_k * 10)
    )
)
```

### Search Process Flow

1. User enables MMR toggle and sets diversity level
2. Frontend sends `use_mmr` and `diversity` in request
3. Backend receives parameters and passes to vector store
4. Vector store uses MMR query instead of standard search
5. Results are returned with balanced relevance and diversity

## Benefits

- **Discoverability**: Find varied perspectives on a topic
- **Comprehensive Coverage**: Avoid redundant, highly similar results
- **Exploration**: Great for brainstorming and research
- **User Control**: Toggle on/off and adjust diversity as needed

## Default Behavior

- MMR is **disabled by default** (`use_mmr=False`)
- Traditional similarity search when disabled
- Diversity set to 0.5 when MMR is enabled
- Users can customize based on their needs

