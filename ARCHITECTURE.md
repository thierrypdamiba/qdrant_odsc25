# System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                           │
│                      (Next.js Frontend)                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │  Login   │  │Dashboard │  │  Query   │  │Knowledge │       │
│  │  Page    │  │   Page   │  │   Page   │  │   Base   │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │              Auth Context + API Client                  │    │
│  └────────────────────────────────────────────────────────┘    │
└────────────────────┬─────────────────────────────────────────┬─┘
                     │ HTTP/REST API                           │
                     ▼                                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                       FastAPI Backend                            │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    API Routes                             │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐                  │  │
│  │  │  Auth   │  │   KB    │  │  Query  │                  │  │
│  │  │ Routes  │  │ Routes  │  │ Routes  │                  │  │
│  │  └─────────┘  └─────────┘  └─────────┘                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  Core Services                            │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │  │
│  │  │  Auth   │  │Document │  │   RAG   │  │ Config  │    │  │
│  │  │ & RBAC  │  │Processor│  │Pipeline │  │  Deps   │    │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                           │                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              External Service Integrations                │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │  │
│  │  │Vector Store  │  │  LLM Service │  │    Search    │  │  │
│  │  │  (Qdrant)   │  │   (Groq)    │  │ (Perplexity) │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                     │              │              │
                     ▼              ▼              ▼
           ┌────────────┐  ┌────────────┐  ┌────────────┐
           │  Qdrant    │  │   Groq     │  │ Perplexity │
           │   Cloud    │  │    API     │  │    API     │
           │(Vector DB) │  │   (LLM)    │  │  (Search)  │
           └────────────┘  └────────────┘  └────────────┘
```

## Component Breakdown

### Frontend Layer (Next.js 14)

**Pages:**
- `/login` - Authentication entry point
- `/dashboard` - User home with permissions overview
- `/query` - Main query interface with mode selection
- `/knowledge-base` - Document upload and management (admin only)

**Key Components:**
- `Navbar` - Navigation with user context
- `AuthProvider` - Global authentication state
- `apiClient` - Centralized HTTP client

**Features:**
- TypeScript for type safety
- Tailwind CSS for styling
- React Context for state management
- Client-side routing with App Router

### Backend Layer (FastAPI)

**API Routes:**
```
/auth/login       → Simplified authentication (test users)
/auth/me          → Get current user
/kb/documents/upload → Upload document (admin)
/kb/documents     → List documents
/kb/documents/{id}/status → Check processing status
/kb/documents/{id} → Delete document (admin)
/query/           → Query system (local/internet/hybrid)
/health           → Health check
```

**Core Services:**

1. **Authentication & RBAC** (`core/auth.py`)
   - Test users with different permission levels
   - Permission validation middleware
   - Token-based auth (simplified)

2. **Document Processor** (`services/document_processor.py`)
   - File upload and storage
   - Text extraction (PDF, DOCX, TXT, MD)
   - Text chunking (512 tokens, 50 overlap)
   - Embedding generation (sentence-transformers)

3. **RAG Service** (`services/rag.py`)
   - Query embedding
   - Vector search
   - Context assembly
   - LLM generation
   - Source citation

4. **Vector Store** (`services/vector_store.py`)
   - Qdrant implementation for vector storage and search

5. **LLM Service** (`services/llm.py`)
   - Groq implementation for fast LLM inference

6. **Search Service** (`services/search.py`)
   - Perplexity implementation for internet search

## Data Flow

### Document Upload Flow

```
User uploads file
       │
       ▼
┌─────────────────────┐
│ Save file to disk   │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│ Store metadata in   │
│ Qdrant (documents)  │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│ Background Task:    │
│ 1. Extract text     │
│ 2. Chunk text       │
│ 3. Generate vectors │
│ 4. Store in Qdrant  │
│ 5. Update status    │
└─────────────────────┘
```

### Query Flow (Local Mode)

```
User submits query
       │
       ▼
┌─────────────────────┐
│ Check permissions   │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│ Generate query      │
│ embedding           │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│ Search Qdrant       │
│ (filter classified) │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│ Retrieve top-k      │
│ chunks              │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│ Assemble context    │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│ LLM generates       │
│ answer with         │
│ citations           │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│ Return answer +     │
│ sources to user     │
└─────────────────────┘
```

### Query Flow (Internet Mode)

```
User submits query
       │
       ▼
┌─────────────────────┐
│ Check internet      │
│ permission          │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│ Call Perplexity     │
│ Search API          │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│ Parse search        │
│ results             │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│ Assemble context    │
│ from results        │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│ LLM generates       │
│ answer              │
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│ Return answer +     │
│ citations           │
└─────────────────────┘
```

### Query Flow (Hybrid Mode)

```
User submits query
       │
       ├──────────────────────┐
       ▼                      ▼
┌──────────────┐    ┌──────────────┐
│ Local RAG    │    │ Internet     │
│ Pipeline     │    │ Search       │
└──────────────┘    └──────────────┘
       │                      │
       └──────────┬───────────┘
                  ▼
        ┌──────────────────┐
        │ Combine results  │
        └──────────────────┘
                  │
                  ▼
        ┌──────────────────┐
        │ LLM synthesizes  │
        │ final answer     │
        └──────────────────┘
                  │
                  ▼
        ┌──────────────────┐
        │ Return to user   │
        └──────────────────┘
```

## Permission Model

### User Types

```
┌──────────────────────────────────────────────────────────────┐
│                         Admin User                            │
│  ✓ Local Search    ✓ Internet Search                        │
│  ✓ Classified Docs ✓ Upload Documents                       │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                      Local Only User                          │
│  ✓ Local Search    ✗ Internet Search                        │
│  ✗ Classified Docs ✗ Upload Documents                       │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                       Hybrid User                             │
│  ✓ Local Search    ✓ Internet Search                        │
│  ✗ Classified Docs ✗ Upload Documents                       │
└──────────────────────────────────────────────────────────────┘
```

### Permission Checks

**Document Upload:**
```python
if not user.permissions.can_upload_documents:
    raise HTTPException(403, "Permission denied")
```

**Internet Search:**
```python
if request.mode == "internet" and not user.permissions.can_search_internet:
    raise HTTPException(403, "Internet search not allowed")
```

**Classified Documents:**
```python
filter_classified = not user.permissions.can_access_classified
if filter_classified:
    results = filter(lambda r: "classified" not in r.tags, results)
```

## Data Storage (Qdrant Collections)

### Collection: `documents`
```
Purpose: Store document metadata
Vector: Dummy (384-dim zeros)
Payload: {
  doc_id, filename, file_type, upload_date,
  status, tags, uploader_id, size_bytes, num_chunks
}
```

### Collection: `{org_id}_text`
```
Purpose: Store text chunk embeddings
Vector: Real (384-dim from sentence-transformers)
Payload: {
  doc_id, filename, content,
  chunk_index, tags
}
```

### Collection: `{org_id}_images` (Future)
```
Purpose: Store image embeddings
Vector: Real (512-dim from CLIP)
Payload: {
  doc_id, image_url, image_description,
  page_num, tags
}
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js 14 | React framework with App Router |
| Frontend | TypeScript | Type safety |
| Frontend | Tailwind CSS | Styling |
| Backend | FastAPI | Python web framework |
| Backend | Pydantic | Data validation |
| Backend | uvicorn | ASGI server |
| Vector DB | Qdrant | Vector storage and search |
| Embeddings | sentence-transformers | Text → vectors |
| Embeddings | CLIP | Image → vectors (future) |
| LLM | Groq API | Fast inference |
| Search | Perplexity API | Internet search |
| Documents | PyPDF2, python-docx | Text extraction |

## Deployment Architecture (Future)

```
┌─────────────────────────────────────────────────────────────┐
│                        CDN (Vercel)                          │
│                     (Frontend Assets)                        │
└─────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                   Load Balancer / API Gateway                │
└─────────────────────────────────────────────────────────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
┌──────────────────────┐      ┌──────────────────────┐
│  FastAPI Instance 1  │      │  FastAPI Instance N  │
│     (Docker/K8s)     │      │     (Docker/K8s)     │
└──────────────────────┘      └──────────────────────┘
              │                             │
              └──────────────┬──────────────┘
                             ▼
              ┌────────────────────────────┐
              │      Qdrant Cloud          │
              │   (Managed Vector DB)      │
              └────────────────────────────┘
```

## Security Considerations

1. **Authentication**: Currently simplified for demo - upgrade to JWT with secrets for production
2. **Authorization**: RBAC implemented with permission checks
3. **Data Isolation**: Org-based collections for multi-tenancy
4. **API Keys**: Stored in environment variables
5. **File Upload**: Size limits and type validation
6. **CORS**: Configured for development (restrict in production)

## Performance Optimizations

1. **Async**: FastAPI async/await for non-blocking I/O
2. **Background Tasks**: Document processing doesn't block requests
3. **Caching**: Embedding models loaded once (lazy loading)
4. **Chunking**: Efficient retrieval with overlapping chunks
5. **Vector Search**: Qdrant's optimized HNSW indexing

## Scalability

1. **Horizontal**: Multiple FastAPI instances behind load balancer
2. **Vertical**: Qdrant scales with cluster mode
3. **Storage**: Separate file storage (S3-compatible)
4. **Queue**: Add Celery/Redis for heavy processing
5. **Caching**: Add Redis for frequently accessed data

---

For implementation details, see `PROJECT_STRUCTURE.md`


