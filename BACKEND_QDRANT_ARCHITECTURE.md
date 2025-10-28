# Backend & Qdrant Architecture

This document explains how the Agentic RAG system backend works, with a focus on the Qdrant integration.

## Table of Contents

1. [System Overview](#system-overview)
2. [Backend Architecture](#backend-architecture)
3. [Qdrant Integration](#qdrant-integration)
4. [Data Flow](#data-flow)
5. [Key Components](#key-components)
6. [Cloud Inference Feature](#cloud-inference-feature)
7. [Query Pipeline](#query-pipeline)
8. [Collections & Data Models](#collections--data-models)

---

## System Overview

The Agentic RAG system consists of:
- **Frontend**: Next.js application running on port 3000
- **Backend**: FastAPI application running on port 8000
- **Vector Store**: Qdrant Cloud for embeddings storage and search
- **LLM**: Groq API for fast inference
- **Search**: Perplexity API for internet search

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   Frontend   │────────▶│   Backend    │────────▶│    Qdrant    │
│  (Next.js)   │  HTTP   │  (FastAPI)   │  HTTP   │   (Cloud)    │
└──────────────┘         └──────────────┘         └──────────────┘
                              │
                              ├────────▶ Groq API (LLM)
                              └────────▶ Perplexity (Search)
```

---

## Backend Architecture

### FastAPI Application Structure

```python
backend/app/
├── main.py              # FastAPI app entry point
├── core/
│   ├── config.py        # Environment configuration
│   ├── auth.py          # Authentication & RBAC
│   └── deps.py          # Dependency injection
├── api/routes/
│   ├── auth.py          # Authentication endpoints
│   ├── kb.py            # Knowledge base endpoints
│   ├── query.py         # Query endpoints
│   └── query_stream.py  # Streaming query endpoints
├── services/
│   ├── vector_store.py  # Qdrant integration
│   ├── rag.py           # RAG pipeline orchestration
│   ├── document_processor.py  # Text extraction & chunking
│   ├── llm.py           # Groq LLM integration
│   └── search.py        # Perplexity integration
└── schemas/
    ├── auth.py          # Pydantic models for auth
    ├── query.py         # Pydantic models for queries
    └── document.py      # Pydantic models for documents
```

### Core Configuration (`app/core/config.py`)

The `Settings` class loads all configuration from environment variables:

```python
class Settings(BaseSettings):
    # Qdrant Configuration
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: Optional[str] = None
    qdrant_cloud_inference: bool = True  # Enable cloud inference
    
    # LLM Configuration
    groq_api_key: Optional[str] = None
    
    # Application Configuration
    environment: str = "development"
    org_id: str = "default_org"
```

Key settings:
- `qdrant_cloud_inference`: When enabled, Qdrant generates embeddings server-side using cloud inference
- `org_id`: Used for multi-tenant isolation (collection naming)

---

## Qdrant Integration

### Vector Store Service (`app/services/vector_store.py`)

The `QdrantVectorStore` class provides the interface between the backend and Qdrant.

#### Initialization

```python
def __init__(self, url: str, api_key: Optional[str] = None, cloud_inference: bool = False):
    from qdrant_client import QdrantClient
    self.client = QdrantClient(url=url, api_key=api_key)
    self.cloud_inference = cloud_inference
```

#### Two Operating Modes

##### 1. Local Embedding Mode (Traditional)

- Client generates embeddings using local models
- Sends pre-computed vectors to Qdrant
- Requires local sentence-transformers model

**Flow:**
```
Query → Embed locally → Search with vectors → Results
```

##### 2. Cloud Inference Mode (Qdrant Cloud)

- Sends raw text to Qdrant
- Qdrant generates embeddings server-side
- No local embedding model needed

**Flow:**
```
Query → Send text → Qdrant embeds & searches → Results
```

### Cloud Inference Implementation

When `cloud_inference=True`, the system uses Qdrant's REST API with special vector format:

```python
# Regular mode - send vectors
{
    "id": "point-123",
    "vector": [0.1, 0.2, 0.3, ...],  # Pre-computed embedding
    "payload": {...}
}

# Cloud inference mode - send text
{
    "id": "point-123",
    "vector": {
        "text": "The actual text content",
        "model": "sentence-transformers/all-minilm-l6-v2"
    },
    "payload": {...}
}
```

**Upsert with Cloud Inference:**

```python
if self.cloud_inference and texts:
    url = f"{self.client.rest_uri}/collections/{collection_name}/points"
    points_data = [{
        "id": point_id,
        "payload": payload,
        "vector": {
            "text": text,
            "model": "sentence-transformers/all-minilm-l6-v2"
        }
    } for point_id, text, payload in zip(ids, texts, payloads)]
    
    response = await client.put(url, json={"points": points_data})
```

**Search with Cloud Inference:**

```python
if self.cloud_inference and query_text:
    data = {
        "query": {
            "text": query_text,  # Raw text query
            "model": "sentence-transformers/all-minilm-l6-v2"
        },
        "limit": top_k,
        "with_payload": True
    }
    response = await http_client.post(url, json=data)
```

### Benefits of Cloud Inference

1. **No Local Model**: No need to load/download sentence-transformers locally
2. **Always Updated**: Qdrant uses the latest embedding model version
3. **Scalable**: Embedding happens in Qdrant's infrastructure
4. **Same API**: Same Qdrant API, just different vector format

### Timing Breakdown

When using cloud inference, the system tracks detailed timings:

```python
# Server-side timing (from Qdrant response)
qdrant_server_time = result.get("time", 0) * 1000

# Estimated breakdown
estimated_embedding_time = qdrant_server_time * 0.65  # ~65% for embedding
estimated_search_time = qdrant_server_time * 0.35      # ~35% for search

# Network time
network_time = total_call_time - qdrant_server_time
```

---

## Data Flow

### Document Upload Flow

```
User uploads PDF/DOCX/TXT
       │
       ▼
┌────────────────────────┐
│  FastAPI receives file │
│  (kb.py route)         │
└────────────────────────┘
       │
       ▼
┌────────────────────────┐
│ Save file to disk     │
│ (DocumentProcessor)    │
└────────────────────────┘
       │
       ▼
┌────────────────────────┐
│ Store document metadata│
│ in Qdrant (documents   │
│ collection)            │
└────────────────────────┘
       │
       ▼
┌────────────────────────┐
│ Background processing: │
│ 1. Extract text        │
│ 2. Chunk text          │
│ 3. Generate vectors    │
│    (or prepare text)   │
│ 4. Upsert to Qdrant    │
└────────────────────────┘
       │
       ▼
┌────────────────────────┐
│ Update document status │
│ in Qdrant              │
└────────────────────────┘
```

### Query Flow

```
User submits query
       │
       ▼
┌────────────────────────┐
│ POST /query/           │
│ - Check permissions    │
│ - Get agent service    │
└────────────────────────┘
       │
       ▼
┌────────────────────────┐
│ AgenticRAG determines  │
│ best mode (auto/local/ │
│ internet/hybrid)       │
└────────────────────────┘
       │
       ▼
┌────────────────────────┐
│ RAG Service:           │
│ 1. Generate query      │
│    embedding (or text) │
│ 2. Search Qdrant       │
│ 3. Retrieve top-k      │
│ 4. Assemble context    │
│ 5. Generate answer      │
│ 6. Cite sources        │
└────────────────────────┘
       │
       ▼
┌────────────────────────┐
│ Return to user:        │
│ - Answer               │
│ - Sources              │
│ - Timings              │
└────────────────────────┘
```

---

## Key Components

### 1. RAG Service (`app/services/rag.py`)

Orchestrates the RAG pipeline:

```python
class RAGService:
    def __init__(
        self,
        vector_store: VectorStore,
        llm_service: LLMService,
        search_service: SearchService,
        embedding_service: EmbeddingService,
        org_id: str = "default_org"
    ):
        # ... initialization
        
    async def query_local(self, query, top_k=5, ...):
        # 1. Generate/use query embedding
        # 2. Search Qdrant for similar chunks
        # 3. Filter classified docs (if needed)
        # 4. Assemble context
        # 5. Generate answer with LLM
        # 6. Return answer + sources
```

**Key Methods:**
- `query_local()`: Search local knowledge base
- `query_internet()`: Search internet via Perplexity
- `query_hybrid()`: Combine local + internet

### 2. Document Processor (`app/services/document_processor.py`)

Handles text extraction and chunking:

```python
class DocumentProcessor:
    def extract_text(self, file_path, file_type) -> str:
        # Extract text from PDF, DOCX, TXT, MD
        
    def chunk_text(self, text, chunk_size=512, overlap=50) -> List[Dict]:
        # Split text into overlapping chunks
        
class EmbeddingService:
    def embed_text(self, texts: List[str]) -> List[List[float]]:
        # Generate embeddings (local mode)
```

### 3. Vector Store (`app/services/vector_store.py`)

Abstract interface for vector operations:

```python
class VectorStore(ABC):
    @abstractmethod
    async def create_collection(...)
    
    @abstractmethod
    async def upsert_vectors(...)
    
    @abstractmethod
    async def search(...)
    
    @abstractmethod
    async def delete(...)
```

**QdrantVectorStore** implementation handles:
- Collection creation
- Point insertion (with cloud inference support)
- Vector similarity search
- MMR (Maximal Marginal Relevance) for diversity

### 4. Collections & Data Models

#### Collection: `documents`

**Purpose**: Document metadata storage

```python
{
    "id": "doc-uuid",
    "vector": [0.0, ...],  # Dummy vector (not used for search)
    "payload": {
        "doc_id": "doc-uuid",
        "filename": "report.pdf",
        "file_type": "pdf",
        "upload_date": "2024-01-01T00:00:00",
        "status": "processed",
        "tags": ["wikipedia", "science"],
        "uploader_id": "user-123",
        "size_bytes": 150000,
        "num_chunks": 45
    }
}
```

#### Collection: `{org_id}_text` (e.g., `default_org_text`)

**Purpose**: Text chunk embeddings

```python
{
    "id": "chunk-uuid",
    "vector": [0.123, ...],  # or {"text": "chunk", "model": "..."}
    "payload": {
        "doc_id": "doc-uuid",
        "filename": "report.pdf",
        "content": "The full chunk text...",
        "chunk_index": 12,
        "tags": ["wikipedia", "science"],
        "source": "simple_wikipedia",
        "page_num": 5
    }
}
```

**Vector Configuration:**
```python
VectorParams(
    size=384,              # all-MiniLM-L6-v2 produces 384-dim vectors
    distance=Distance.COSINE  # Cosine similarity for semantic search
)
```

---

## Cloud Inference Feature

### How It Works

When `qdrant_cloud_inference=True`:

1. **Upload Phase**:
   ```python
   # Instead of local embedding
   embeddings = model.encode(texts)  # ❌ Not needed
   
   # Send text directly to Qdrant
   {
       "vector": {
           "text": "Actual text content",
           "model": "sentence-transformers/all-minilm-l6-v2"
       }
   }
   ```

2. **Query Phase**:
   ```python
   # Instead of embedding query
   query_vector = model.encode(query)  # ❌ Not needed
   
   # Send query text directly
   {
       "query": {
           "text": "What is Python?",
           "model": "sentence-transformers/all-minilm-l6-v2"
       }
   }
   ```

### Configuration

```bash
# .env file
QDRANT_URL=https://your-cluster.qdrant.io
QDRANT_API_KEY=your-api-key
QDRANT_CLOUD_INFERENCE=true
```

### Performance Benefits

| Mode | Local Embedding Time | Network Time | Total |
|------|---------------------|--------------|-------|
| Local | ~50-100ms | ~50ms | ~100-150ms |
| Cloud | 0ms (handled by Qdrant) | ~100-150ms | ~100-150ms |

**Cloud inference advantages:**
- No model download (saves ~100MB)
- No model loading time
- Always uses latest model version
- Consistent performance across instances

---

## Query Pipeline

### Step-by-Step: Local Query

```python
# 1. User submits query
POST /query/
{
    "query": "What is machine learning?",
    "mode": "local",
    "top_k": 5
}

# 2. RAG Service receives query
async def query_local(query, top_k=5, ...):
    collection_name = f"{org_id}_text"  # "default_org_text"
    
    # 3. Generate query embedding (or use text)
    if cloud_inference:
        query_text = query  # Send text directly
    else:
        query_vector = embed(query)  # Generate embedding
    
    # 4. Search Qdrant
    results = await vector_store.search(
        collection_name=collection_name,
        query_vector=query_vector or [],
        query_text=query_text,  # For cloud inference
        top_k=top_k
    )
    # Returns: [
    #   {"id": "...", "score": 0.95, "payload": {...}},
    #   ...
    # ]
    
    # 5. Filter classified documents
    results = [r for r in results if "classified" not in r["payload"].get("tags", [])]
    
    # 6. Assemble context
    context = "\n\n".join([f"[Source {i+1}] {r['payload']['content']}" 
                          for i, r in enumerate(results)])
    
    # 7. Generate answer
    answer = await llm.generate(context + "\n\nUser Question: " + query)
    
    # 8. Extract sources
    sources = [Source(doc_name=r['payload']['filename'], ...) 
               for r in results]
    
    # 9. Return response
    return {
        "answer": answer,
        "sources": sources,
        "mode": "local"
    }
```

### MMR (Maximal Marginal Relevance)

For more diverse results:

```python
results = await vector_store.search(
    collection_name=collection_name,
    query_vector=query_vector,
    top_k=5,
    use_mmr=True,
    diversity=0.5  # 0.0 = relevant, 1.0 = diverse
)
```

**How it works:**
1. Retrieve top N candidates (e.g., top 50)
2. Select most relevant result
3. For each remaining result, calculate: `score - λ * max(similarity to selected)`
4. Select highest scoring remaining result
5. Repeat until top_k results

**Benefits:**
- Reduces redundancy
- Better coverage of topics
- Useful for long documents

---

## Collections & Data Models

### Collection Naming Convention

```python
# Documents metadata
collection_name = "documents"

# Text chunks (per organization)
collection_name = f"{org_id}_text"  # "default_org_text"

# Images (per organization, future)
collection_name = f"{org_id}_images"  # "default_org_images"
```

### Point Structure

**Text Chunk Point:**

```python
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "vector": [0.1, 0.2, ...],  # 384 dimensions
    "payload": {
        "doc_id": "document-uuid",
        "filename": "python-guide.pdf",
        "content": "Python is a high-level programming language...",
        "chunk_index": 5,
        "tags": ["programming", "python"],
        "source": "simple_wikipedia",
        "page_num": 3
    }
}
```

**Document Metadata Point:**

```python
{
    "id": "document-uuid",
    "vector": [0.0, ...],  # Dummy vector
    "payload": {
        "doc_id": "document-uuid",
        "filename": "python-guide.pdf",
        "file_type": "pdf",
        "upload_date": "2024-01-01T00:00:00",
        "status": "processed",
        "tags": ["programming"],
        "uploader_id": "user-123",
        "size_bytes": 500000,
        "num_chunks": 25
    }
}
```

---

## Multi-Tenancy

### Organization Isolation

Each organization has its own collection:

```python
# Settings
org_id = "default_org"

# Collection name
collection_name = f"{org_id}_text"  # "default_org_text"

# In production, multiple organizations:
# - acme_corp_text
# - globex_text
# - etc.
```

### Query Filters

Filter by organization:

```python
filter_conditions = {
    "org_id": org_id
}
results = await vector_store.search(
    collection_name=f"{org_id}_text",
    query_vector=query_vector,
    filter_conditions=filter_conditions
)
```

---

## Performance Considerations

### Embedding Performance

| Model | Dimensions | Speed | Quality |
|-------|-----------|-------|---------|
| all-MiniLM-L6-v2 | 384 | Fast | Good |
| all-mpnet-base-v2 | 768 | Medium | Better |

**Qdrant Cloud Inference Benefits:**
- No local model download
- No local model loading
- Automatic model updates
- Consistent performance

### Search Performance

Qdrant uses HNSW (Hierarchical Navigable Small World) indexing:

```
Query → HNSW Graph → Fast approximate nearest neighbor search
```

**Performance:**
- Typical latency: 50-200ms
- Scales to millions of vectors
- Sub-millisecond search for <100k vectors

---

## Error Handling

### Common Issues

1. **Collection doesn't exist**
   ```python
   # Auto-create on first upsert
   try:
       await vector_store.create_collection(...)
   except Exception:
       pass  # Already exists
   ```

2. **API Key issues**
   ```python
   # Check in health endpoint
   @app.get("/health")
   async def health():
       return {
           "groq_configured": bool(settings.groq_api_key),
           "perplexity_configured": bool(settings.perplexity_api_key)
       }
   ```

3. **Empty results**
   ```python
   # Graceful fallback
   if not results:
       return {
           "answer": "No relevant information found.",
           "sources": [],
           "mode": "local"
       }
   ```

---

## Summary

### Key Takeaways

1. **Cloud Inference**: Qdrant can generate embeddings server-side, eliminating the need for local models
2. **Two Collections**: `documents` for metadata, `{org_id}_text` for embeddings
3. **Flexible Modes**: Support for local, internet, and hybrid search
4. **Multi-Tenant**: Organization-based collection naming
5. **RBAC**: Permission-based access control integrated with query routing

### Architecture Benefits

- **Scalable**: Stateless backend, can horizontally scale
- **Fast**: Cloud inference reduces client-side processing
- **Flexible**: Support for different search modes
- **Maintainable**: Clear separation of concerns (services vs. routes)

---

For more details, see:
- `ARCHITECTURE.md` - High-level system architecture
- `PROJECT_STRUCTURE.md` - Project organization
- `backend/app/services/` - Service implementations

