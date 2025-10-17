# Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites
- Python 3.8+ (for backend)
- Node.js 18+ (for frontend)
- (Optional) Docker (for running real Qdrant)

### Setup Steps

#### 1. Start Qdrant (Vector Database)

```bash
docker-compose up -d
```

This starts Qdrant on `localhost:6333`

#### 2. Configure API Keys

Create `.env` file in `backend/` directory:

```bash
QDRANT_URL=http://localhost:6333
GROQ_API_KEY=your_groq_api_key_here
PERPLEXITY_API_KEY=your_perplexity_api_key_here
```

Get your API keys:
- **Groq**: https://console.groq.com/ (free tier available)
- **Perplexity**: https://www.perplexity.ai/settings/api

#### 3. Start the Backend

```bash
./start-backend.sh
```

The backend will be available at:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

#### 4. Start the Frontend (in a new terminal)

```bash
./start-frontend.sh
```

The frontend will be available at http://localhost:3000

#### 5. Login

Open http://localhost:3000 and login with one of these test users:

| Username | Password | Access Level |
|----------|----------|--------------|
| `admin` | any | Full access (local + internet + classified + upload) |
| `local_user` | any | Local search only |
| `hybrid_user` | any | Local + internet (no classified docs) |

## 📝 Testing the API

Run the test script to verify everything works:

```bash
./test-api.sh
```

This will test:
- Health endpoint
- Authentication
- User permissions
- Local queries
- Internet queries
- Permission restrictions

## 🎯 Usage Examples

### Upload a Document (Admin only)

1. Login as `admin`
2. Go to Knowledge Base
3. Upload a PDF, DOCX, TXT, or MD file
4. Add tags (use "classified" to restrict access)

### Query the System

1. Go to Query page
2. Type your question
3. Select mode:
   - **Local**: Search knowledge base only
   - **Internet**: Search the web
   - **Hybrid**: Search both sources

### Example Queries

**For Local Search:**
- "What is in my documents?"
- "Summarize the uploaded files"

**For Internet Search:**
- "What are the latest AI developments?"
- "Current news about machine learning"

**For Hybrid:**
- "Compare the information in my docs with current internet data"

## 🔧 Manual Setup (if scripts don't work)

### Backend

```bash
# Start Qdrant first
docker-compose up -d

# Setup backend
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env with API keys
cat > .env << EOF
QDRANT_URL=http://localhost:6333
GROQ_API_KEY=your_groq_api_key_here
PERPLEXITY_API_KEY=your_perplexity_api_key_here
EOF

# Run
python -m app.main
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## 🐛 Troubleshooting

### Backend won't start
- Check Python version: `python3 --version` (need 3.8+)
- Try installing dependencies manually: `pip install -r backend/requirements.txt`

### Frontend won't start
- Check Node version: `node --version` (need 18+)
- Delete `node_modules` and reinstall: `cd frontend && rm -rf node_modules && npm install`

### Cannot login
- Make sure backend is running on port 8000
- Check browser console for errors
- Try clearing localStorage

### CORS errors
- Backend should allow all origins by default
- Check that backend is running on http://localhost:8000
- Update `NEXT_PUBLIC_API_URL` in `frontend/.env.local` if needed

## 📚 Next Steps

1. **Upload Documents**: Add PDFs, DOCX files to build your knowledge base
2. **Try Different Users**: Login as different users to see permission differences
3. **Experiment with Modes**: Test local, internet, and hybrid search
4. **Add Real Services**: Get API keys and switch from mock to real services

## 🔗 Useful Links

- Backend API Docs: http://localhost:8000/docs
- Backend Health Check: http://localhost:8000/health
- Frontend: http://localhost:3000
- Qdrant Dashboard: http://localhost:6333/dashboard (if running with Docker)

## 🎓 Understanding the System

### Architecture
```
Frontend (Next.js) → Backend (FastAPI) → Vector Store (Qdrant)
                                      → LLM (Groq)
                                      → Search (Perplexity)
```

### Data Flow
1. **Upload**: Documents → Extract Text → Chunk → Embed → Store in Qdrant
2. **Query**: Question → Embed → Search Qdrant → Retrieve Chunks → LLM → Answer
3. **Internet**: Question → Perplexity API → Results → LLM → Answer
4. **Hybrid**: Both paths combined and synthesized

### User Permissions

| Feature | Admin | Local User | Hybrid User |
|---------|-------|------------|-------------|
| Local Search | ✅ | ✅ | ✅ |
| Internet Search | ✅ | ❌ | ✅ |
| Classified Docs | ✅ | ❌ | ❌ |
| Upload Docs | ✅ | ❌ | ❌ |

---

**Need help?** Check the main README.md for more detailed information.


