# Project Structure

## Overview

```
agent/
├── backend/                    # FastAPI Python Backend
│   ├── app/
│   │   ├── api/               # API Routes
│   │   │   └── routes/
│   │   │       ├── auth.py    # Authentication endpoints
│   │   │       ├── kb.py      # Knowledge base management
│   │   │       └── query.py   # Query endpoints
│   │   ├── core/              # Core configuration
│   │   │   ├── auth.py        # Mock authentication & RBAC
│   │   │   ├── config.py      # Settings & environment variables
│   │   │   └── deps.py        # Dependency injection
│   │   ├── schemas/           # Pydantic models
│   │   │   ├── auth.py        # Auth schemas
│   │   │   ├── document.py    # Document schemas
│   │   │   └── query.py       # Query schemas
│   │   ├── services/          # Business logic
│   │   │   ├── document_processor.py  # Upload, extract, chunk
│   │   │   ├── llm.py         # LLM service (Mock + Groq)
│   │   │   ├── rag.py         # RAG pipeline orchestration
│   │   │   ├── search.py      # Search service (Mock + Perplexity)
│   │   │   └── vector_store.py # Vector store (Mock + Qdrant)
│   │   └── main.py            # FastAPI app entry point
│   ├── requirements.txt       # Python dependencies
│   └── .env                   # Environment variables
│
├── frontend/                  # Next.js 14 Frontend
│   ├── app/                   # App Router pages
│   │   ├── dashboard/         # Dashboard page
│   │   ├── knowledge-base/    # KB management page
│   │   ├── login/             # Login page
│   │   ├── query/             # Query interface page
│   │   ├── layout.tsx         # Root layout
│   │   └── page.tsx           # Landing page (redirect)
│   ├── components/            # React components
│   │   └── Navbar.tsx         # Navigation bar
│   ├── lib/                   # Utilities
│   │   ├── api.ts             # API client
│   │   └── auth-context.tsx   # Auth context provider
│   ├── package.json           # Node dependencies
│   └── .env.local             # Frontend environment variables
│
├── docker-compose.yml         # Docker setup for Qdrant
├── start-backend.sh           # Backend startup script
├── start-frontend.sh          # Frontend startup script
├── test-api.sh                # API testing script
├── README.md                  # Main documentation
├── QUICKSTART.md              # Quick start guide
└── PROJECT_STRUCTURE.md       # This file
```

## Backend Architecture

### Layered Architecture

```
API Layer (routes/)
    ↓
Business Logic (services/)
    ↓
Data Layer (vector_store.py)
```

### Service Pattern

All external services follow an abstract interface with multiple implementations:

- **VectorStore**: `MockVectorStore`, `QdrantVectorStore`
- **LLMService**: `MockLLMService`, `GroqLLMService`
- **SearchService**: `MockSearchService`, `PerplexitySearchService`

This allows easy switching between mock and real services via environment variables.

### Authentication Flow

```
1. User sends credentials → /auth/login
2. Backend validates → returns mock token (username)
3. Subsequent requests include: Authorization: Bearer {token}
4. Middleware validates token → extracts user + permissions
5. Route handlers check permissions before executing
```

### Document Processing Pipeline

```
1. Upload file → /kb/documents/upload
2. Save file to disk
3. Store metadata in Qdrant (documents collection)
4. Background task:
   a. Extract text (PDF/DOCX/TXT)
   b. Chunk text (512 tokens, 50 overlap)
   c. Generate embeddings (sentence-transformers)
   d. Store vectors in Qdrant ({org_id}_text collection)
   e. Update document status → completed
```

### RAG Query Pipeline

```
1. User submits query → /query/
2. Check permissions (mode + classified docs)
3. Generate query embedding
4. Search vector store (filter by classified tag if needed)
5. Retrieve top-k chunks
6. Assemble context
7. Generate answer with LLM
8. Return answer + sources
```

### Hybrid Search Strategy

```
Local Path:
Query → Embed → Qdrant Search → Retrieve Chunks → Context

Internet Path:
Query → Perplexity API → Search Results → Context

Fusion:
Both Contexts → Combined Prompt → LLM → Synthesized Answer
```

## Frontend Architecture

### App Router Structure

Next.js 14 App Router with TypeScript:

```
app/
├── layout.tsx          # Root layout with AuthProvider
├── page.tsx            # Landing (redirects to login/dashboard)
├── login/              # Public login page
├── dashboard/          # Protected - main dashboard
├── query/              # Protected - query interface
└── knowledge-base/     # Protected - document management (admin only)
```

### State Management

- **Auth**: React Context (`lib/auth-context.tsx`)
- **API**: Centralized client (`lib/api.ts`)
- **Local State**: React useState for component state

### Component Hierarchy

```
RootLayout (AuthProvider)
  ├── Navbar (on protected pages)
  ├── Page-specific content
  └── Modals/Overlays (future)
```

### Authentication Guard

```typescript
useEffect(() => {
  if (!loading && !user) {
    router.push('/login');
  }
}, [user, loading, router]);
```

Every protected page checks auth status and redirects if needed.

## Data Storage (Qdrant)

### Collections

```
documents                # Document metadata
{org_id}_text           # Text chunk embeddings
{org_id}_images         # Image embeddings (future)
query_history           # Query logs (future)
```

### Document Collection Schema

```json
{
  "id": "doc_id",
  "vector": [0.0, ...],  // Dummy vector
  "payload": {
    "doc_id": "uuid",
    "filename": "document.pdf",
    "file_type": "pdf",
    "upload_date": "2025-01-01T00:00:00",
    "status": "completed",
    "tags": ["classified", "internal"],
    "uploader_id": "user_1",
    "size_bytes": 12345,
    "num_chunks": 42
  }
}
```

### Text Chunk Collection Schema

```json
{
  "id": "doc_id_chunk_0",
  "vector": [0.123, 0.456, ...],  // 384-dim embedding
  "payload": {
    "doc_id": "uuid",
    "filename": "document.pdf",
    "content": "actual text content...",
    "chunk_index": 0,
    "tags": ["classified"]
  }
}
```

## API Endpoints

### Authentication
- `POST /auth/login` - Login
- `GET /auth/me` - Current user info

### Knowledge Base
- `POST /kb/documents/upload` - Upload document
- `GET /kb/documents` - List documents
- `GET /kb/documents/{id}/status` - Get processing status
- `DELETE /kb/documents/{id}` - Delete document

### Query
- `POST /query/` - Query system (local/internet/hybrid)

### System
- `GET /` - Root info
- `GET /health` - Health check

## Environment Variables

### Backend (.env)

```bash
# Qdrant
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

# LLM
GROQ_API_KEY=

# Search
PERPLEXITY_API_KEY=

# Config
ENVIRONMENT=development
ORG_ID=default_org

# Mock Services
USE_MOCK_VECTOR_STORE=true
USE_MOCK_LLM=true
USE_MOCK_SEARCH=true
```

### Frontend (.env.local)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## User Roles & Permissions

### Mock Users

```python
MOCK_USERS = {
    "admin": User(
        permissions=UserPermissions(
            can_search_local=True,
            can_search_internet=True,
            can_access_classified=True,
            can_upload_documents=True
        )
    ),
    "local_user": User(
        permissions=UserPermissions(
            can_search_local=True,
            can_search_internet=False,
            can_access_classified=False,
            can_upload_documents=False
        )
    ),
    "hybrid_user": User(
        permissions=UserPermissions(
            can_search_local=True,
            can_search_internet=True,
            can_access_classified=False,
            can_upload_documents=False
        )
    )
}
```

### Permission Matrix

| Action | Endpoint | Requires |
|--------|----------|----------|
| Local Search | POST /query/ (mode=local) | can_search_local |
| Internet Search | POST /query/ (mode=internet) | can_search_internet |
| Hybrid Search | POST /query/ (mode=hybrid) | can_search_internet |
| Access Classified | POST /query/ | can_access_classified |
| Upload Doc | POST /kb/documents/upload | can_upload_documents |
| Delete Doc | DELETE /kb/documents/{id} | can_upload_documents |

## Technology Stack

### Backend
- **Framework**: FastAPI 0.115+
- **Async**: uvicorn with async/await
- **Validation**: Pydantic 2.9+
- **Vector Store**: Qdrant
- **Embeddings**: sentence-transformers
- **LLM**: Groq API
- **Search**: Perplexity API
- **Document Processing**: PyPDF2, python-docx, pdfplumber

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State**: React Context API
- **HTTP**: Fetch API

### Infrastructure
- **Vector DB**: Qdrant (Docker or Cloud)
- **Storage**: Local filesystem (uploads)
- **Database**: None (Qdrant for everything)

## Development Workflow

1. **Start Backend**: `./start-backend.sh`
2. **Start Frontend**: `./start-frontend.sh`
3. **Test API**: `./test-api.sh`
4. **Make Changes**: Edit code, auto-reload enabled
5. **Check Logs**: Terminal output from both servers

## Testing Strategy

### Manual Testing
- Use `test-api.sh` for backend
- Use browser for frontend
- Check `/docs` for API playground

### Future Testing
- Backend: pytest with fixtures
- Frontend: Jest + React Testing Library
- E2E: Playwright

## Deployment Considerations

### Backend
- Use gunicorn/uvicorn workers
- Set up proper Qdrant Cloud instance
- Add real JWT with secrets
- Enable HTTPS
- Add rate limiting
- Set up logging/monitoring

### Frontend
- Build: `npm run build`
- Deploy to Vercel/Netlify
- Set environment variables
- Enable analytics

### Database
- Use Qdrant Cloud for production
- Set up backups
- Monitor storage usage

## Future Enhancements

- [ ] Real JWT authentication
- [ ] Multi-organization support
- [ ] Image embedding and search
- [ ] Streaming responses (SSE)
- [ ] Query history tracking
- [ ] Usage analytics dashboard
- [ ] Document preview
- [ ] Batch document upload
- [ ] Advanced filtering
- [ ] Export results
- [ ] API rate limiting
- [ ] Comprehensive testing
- [ ] CI/CD pipeline

---

For questions or contributions, see the main README.md


