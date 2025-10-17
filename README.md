# Agentic RAG System

A production-ready multimodal RAG (Retrieval-Augmented Generation) system with internet search capabilities, multi-tenancy support, and role-based access control.

## Features

- **Multimodal Knowledge Base**: Support for text (PDF, DOCX, TXT, MD) and images
- **Hybrid Search**: Local RAG + Internet search (Perplexity API)
- **RBAC**: Three user roles with different permissions
- **Vector Storage**: Qdrant for all data (no SQL database needed)
- **Fast LLM**: Groq API for rapid inference

## Architecture

```
Backend: FastAPI + Python
Frontend: Next.js 14 + TypeScript + Tailwind CSS
Vector Store: Qdrant (cloud or local)
LLM: Groq API
Search: Perplexity API
```

## User Roles & Permissions

| Role | Local Search | Internet Search | Classified Docs | Upload Docs |
|------|-------------|-----------------|-----------------|-------------|
| **Admin** | ✅ | ✅ | ✅ | ✅ |
| **Local Only** | ✅ | ❌ | ❌ | ❌ |
| **Hybrid** | ✅ | ✅ | ❌ | ❌ |

### Test Users (Simplified Auth)

- **Username**: `admin` | **Password**: any | **Role**: Admin (full access)
- **Username**: `local_user` | **Password**: any | **Role**: Local only
- **Username**: `hybrid_user` | **Password**: any | **Role**: Hybrid search

## Quick Start

### Backend Setup

1. **Install dependencies**:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure environment**:
```bash
# Create .env file with your API keys
cat > .env << EOF
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
GROQ_API_KEY=your_groq_api_key_here
PERPLEXITY_API_KEY=your_perplexity_api_key_here
EOF
```

3. **Start Qdrant**:
```bash
docker-compose up -d
```

4. **Run the server**:
```bash
cd backend
python -m app.main
```

The API will be available at `http://localhost:8000`
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Frontend Setup

1. **Install dependencies**:
```bash
cd frontend
npm install
```

2. **Configure environment**:
```bash
cp .env.example .env.local
# Update NEXT_PUBLIC_API_URL if needed
```

3. **Run the development server**:
```bash
npm run dev
```

The app will be available at `http://localhost:3000`

## API Endpoints

### Authentication
- `POST /auth/login` - Login and get access token
- `GET /auth/me` - Get current user info

### Knowledge Base
- `POST /kb/documents/upload` - Upload document (Admin only)
- `GET /kb/documents` - List all documents
- `GET /kb/documents/{id}/status` - Get processing status
- `DELETE /kb/documents/{id}` - Delete document (Admin only)

### Query
- `POST /query` - Query the system (local/internet/hybrid)

## Configuration

### Environment Variables

```bash
# Qdrant Configuration
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

# LLM Configuration (required)
GROQ_API_KEY=your_groq_api_key_here

# Search Configuration (required)
PERPLEXITY_API_KEY=your_perplexity_api_key_here
```

### Getting API Keys

1. **Qdrant**:
   - **Local**: `docker-compose up -d` (no API key needed)
   - **Cloud**: Use Qdrant Cloud and get your API key

2. **Groq**: https://console.groq.com/ (free tier available)

3. **Perplexity**: https://www.perplexity.ai/settings/api

## Development

### Project Structure

```
backend/
├── app/
│   ├── api/routes/       # API endpoints
│   ├── core/             # Config, auth, dependencies
│   ├── schemas/          # Pydantic models
│   ├── services/         # Business logic
│   └── main.py          # FastAPI app
├── requirements.txt
└── .env

frontend/
├── app/                  # Next.js 14 App Router
├── components/           # React components
├── lib/                  # Utilities
└── package.json
```

### Testing the API

Using curl:

```bash
# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"any"}'

# Query (use token from login)
curl -X POST http://localhost:8000/query/ \
  -H "Authorization: Bearer admin" \
  -H "Content-Type: application/json" \
  -d '{"query":"What is machine learning?","mode":"local","top_k":5}'

# Upload document (Admin only)
curl -X POST http://localhost:8000/kb/documents/upload \
  -H "Authorization: Bearer admin" \
  -F "file=@document.pdf" \
  -F "tags=classified,internal"
```

## Roadmap

- [x] Backend API with FastAPI
- [x] Mock authentication with RBAC
- [x] Vector store integration (Qdrant)
- [x] Document processing pipeline
- [x] RAG query pipeline
- [x] Internet search integration
- [ ] Frontend UI with Next.js
- [ ] Real-time streaming responses
- [ ] Image embedding and search
- [ ] Advanced analytics dashboard
- [ ] Real JWT authentication
- [ ] Multi-organization support

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.


