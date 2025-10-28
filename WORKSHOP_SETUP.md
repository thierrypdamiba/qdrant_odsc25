# Workshop Setup Guide

This guide will walk you through setting up and running the Agentic RAG system for the workshop.

## ⚠️ Workshop Notice

**IMPORTANT**: For the workshop, please load **only 100 articles** to keep data loading fast and manageable. The workshop cluster is shared, so loading too many articles will slow things down for everyone.

## Setup Method

**We are using Qdrant Cloud (NOT Docker)** for this workshop. All services run locally on your machine while connecting to Qdrant Cloud for vector storage.

## Quick Setup (TL;DR)

If you're familiar with Python/Node projects, here's the condensed version:

```bash
# 1. Backend setup
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements-workshop.txt

# 2. Create .env file with Qdrant Cloud credentials (see Step 2)

# 3. Load data
python scripts/load_simple_wikipedia.py

# 4. Start backend (keep running)
python -m app.main

# 5. Frontend setup (new terminal)
cd frontend && npm install && npm run dev
```

Then open http://localhost:3000 and login with any username/password.

For detailed instructions, continue reading below.

## Prerequisites

- Python 3.8+ installed
- Node.js 18+ installed
- Git installed
- Access to Qdrant Cloud (we'll use the cluster URL and API key provided)
- API keys for Groq and Perplexity (we'll set these up)

## Step 1: Clone and Navigate to the Project

```bash
# If not already done, clone the repository
git clone <repository-url>
cd agent
```

## Step 2: Set Up Environment Variables

The backend requires API keys and configuration. Create a `.env` file in the `backend/` directory:

```bash
cd backend
nano .env  # or use any text editor
```

Add the following configuration:

```bash
# Qdrant Configuration (Cloud instance provided for workshop)
QDRANT_URL=
QDRANT_API_KEY=
QDRANT_CLOUD_INFERENCE=true

# LLM Configuration (Groq - Fast inference)
GROQ_API_KEY=your_groq_api_key_here

# Search Configuration (Perplexity - Internet search)
PERPLEXITY_API_KEY=your_perplexity_api_key_here

# Application Configuration
ENVIRONMENT=development
ORG_ID=default_org

# Mock Services (set to false to use real services)
USE_MOCK_VECTOR_STORE=false
USE_MOCK_LLM=true
USE_MOCK_SEARCH=false
```

### Getting API Keys

#### Groq API Key (for LLM)
1. Go to https://console.groq.com/
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy and paste it into the `GROQ_API_KEY` field

#### Perplexity API Key (for Internet Search)
1. Go to https://www.perplexity.ai/
2. Sign up or log in
3. Go to Settings → API Keys
4. Create a new API key
5. Copy and paste it into the `PERPLEXITY_API_KEY` field

**Note**: If you don't have these keys yet, the app will work in mock mode (USE_MOCK_LLM=true, USE_MOCK_SEARCH=false). You can add the keys later and update the .env file.

## Step 3: Install Backend Dependencies

```bash
# From the project root
cd backend

# Create virtual environment (if not exists)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
# Option 1: Use workshop-optimized requirements (recommended - faster install)
pip install -r requirements-workshop.txt

# Option 2: Use full requirements (includes everything)
# pip install -r requirements.txt
```

**Note**: The `requirements-workshop.txt` includes only the packages needed for the workshop, making installation faster (~2-3 minutes vs 5-7 minutes).

## Step 4: Load Sample Data

**IMPORTANT**: Load only 100 articles for the workshop.

Before running the application, we need to load some sample data into the Qdrant collection:

```bash
# Make sure you're in the backend directory with venv activated
cd backend
source venv/bin/activate

# Load 100 Wikipedia articles (this takes about 30-60 seconds)
# Note: The default is now set to 100 articles, so you can run without --num-articles
python scripts/load_simple_wikipedia.py --num-articles 100

# Or simply:
python scripts/load_simple_wikipedia.py
```

You should see output like:
````
======================================================================
Loading Simple Wikipedia into Qdrant
======================================================================
...
✓ Articles processed: 100
✓ Total chunks created: ~500-800
✓ Collection: default_org_text
```

This loads Wikipedia articles that you can query in the app.

## Step 5: Install Frontend Dependencies

```bash
# From the project root
cd frontend

# Install dependencies
npm install
```

## Step 6: Start the Backend

```bash
# From the project root
cd backend
source venv/bin/activate

# Start the FastAPI server
python -m app.main
```

The backend will start on `http://localhost:8000`
- API Documentation: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## Step 7: Start the Frontend

Open a **new terminal window** and run:

```bash
# From the project root
cd frontend

# Start the Next.js development server
npm run dev
```

The frontend will start on `http://localhost:3000`

## Step 8: Access the Application

1. Open your browser and go to http://localhost:3000
2. You'll be redirected to the login page
3. Login with one of these test users:

| Username | Password | Access Level |
|----------|----------|--------------|
| `admin` | any | Full access (local + internet + upload) |
| `local_user` | any | Local search only |
| `hybrid_user` | any | Local + internet search |

## Step 9: Try the Application

### Query the Knowledge Base

1. Navigate to the Query page
2. Try some example queries:
   - "What is Python?"
   - "Tell me about artificial intelligence"
   - "What is the capital of France?"

### Test Different Modes

- **Local Mode**: Searches only your uploaded documents/Wikipedia articles
- **Internet Mode**: Searches the web (requires Perplexity API key)
- **Hybrid Mode**: Combines both local and internet results

### Upload Documents (Admin only)

1. Login as `admin`
2. Go to Knowledge Base page
3. Click "Upload Document"
4. Select a PDF, DOCX, TXT, or MD file
5. Add tags (e.g., "science", "history")
6. Wait for processing to complete

## Troubleshooting

### Backend Won't Start

1. Check Python version: `python3 --version` (need 3.8+)
2. Check virtual environment is activated: `which python` should show venv path
3. Reinstall dependencies: `pip install -r requirements.txt`

### Frontend Won't Start

1. Check Node version: `node --version` (need 18+)
2. Delete and reinstall: `rm -rf node_modules && npm install`

### Cannot Login

1. Make sure backend is running on port 8000
2. Check browser console for errors (F12)
3. Try clearing localStorage in browser DevTools

### No Search Results

1. Make sure you loaded the data with Step 4
2. Check Qdrant connection in backend logs
3. Verify collection exists: Look for "default_org_text" collection in backend logs

### CORS Errors

1. Make sure backend is running
2. Backend should allow all origins by default
3. Check `CORS_ORIGINS` in backend settings if issues persist

## Quick Test Commands

### Test API with cURL

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"test"}'

# Test query
curl -X POST http://localhost:8000/query/ \
  -H "Authorization: Bearer admin" \
  -H "Content-Type: application/json" \
  -d '{"query":"What is Python?","mode":"local","top_k":3}'
```

### Check Qdrant Collection

```bash
# List collections
curl -X GET "https://41933e38-7320-4675-b795-ffa6a7ed86d3.us-west-2-0.aws.cloud.qdrant.io:6333/collections" \
  -H "api-key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.2UUNhLzxzlBnwkgVMYJBSpuxwaqnj1GfJQ6HCzW5Oks"

# Check collection info
curl -X GET "https://41933e38-7320-4675-b795-ffa6a7ed86d3.us-west-2-0.aws.cloud.qdrant.io:6333/collections/default_org_text" \
  -H "api-key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.2UUNhLzxzlBnwkgVMYJBSpuxwaqnj1GfJQ6HCzW5Oks"
```

## Workshop Exercises

### Exercise 1: Basic Query
- Try querying "What is machine learning?"
- Note the sources and how they're presented
- Try different search modes

### Exercise 2: Add Your Own Documents
- Upload a PDF document (as admin)
- Wait for processing
- Query the document you uploaded

### Exercise 3: Compare Modes
- Ask "What is the latest news about AI?" in:
  - Local mode (will use your documents)
  - Internet mode (will search the web)
  - Hybrid mode (combines both)

### Exercise 4: Explore Permissions
- Login as different users (admin, local_user, hybrid_user)
- Notice what features are available to each
- Try actions that should be restricted

### Exercise 5: Check the Data
- Go to Knowledge Base page
- See list of uploaded documents
- Check their metadata and status

## What's in the Collection?

The `default_org_text` collection contains:
- Text chunks from Wikipedia articles (loaded in Step 4)
- Each chunk includes:
  - `content`: The actual text
  - `filename`: Source document name
  - `chunk_index`: Position in document
  - `tags`: Categories like "wikipedia"
  - `source`: Origin (e.g., "simple_wikipedia")
  - `doc_id`: Unique document identifier

When you query:
1. Your question is embedded using `all-MiniLM-L6-v2` model (384 dimensions)
2. Qdrant Cloud Inference embeds it server-side
3. Similar chunks are retrieved from the collection
4. The LLM generates an answer using those chunks

## Architecture Overview

```
┌─────────────┐
│  Frontend   │  (Next.js on :3000)
│   Next.js   │
└──────┬──────┘
       │ HTTP/REST
       ▼
┌─────────────┐
│   Backend   │  (FastAPI on :8000)
│  FastAPI    │
└──────┬──────┘
       │
       ├──► Qdrant Cloud (Vector Store)
       │     - Stores embeddings
       │     - Cloud inference for embeddings
       │
       ├──► Groq API (LLM)
       │     - Generates answers
       │
       └──► Perplexity API (Search)
             - Internet search
```

## Next Steps

1. Complete the setup steps above
2. Try the example exercises
3. Experiment with your own documents
4. Explore the codebase to understand how it works
5. Check the `docs/` folder for more detailed documentation

## Useful Links

- Backend API Docs: http://localhost:8000/docs
- Frontend App: http://localhost:3000
- Health Check: http://localhost:8000/health
- Qdrant Cloud: https://cloud.qdrant.io/

## Summary of Key Files

- `backend/.env` - Environment configuration
- `backend/app/main.py` - FastAPI application
- `backend/scripts/load_simple_wikipedia.py` - Data loading script
- `frontend/app/page.tsx` - Frontend pages
- `frontend/components/` - React components

---

**Need Help?** Ask your workshop instructor or check the other documentation files in the repository.

