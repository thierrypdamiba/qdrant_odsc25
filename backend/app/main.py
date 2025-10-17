"""Main FastAPI application"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import auth, kb, query, query_stream
from app.core.config import settings

app = FastAPI(
    title="Agentic RAG System",
    description="Multi-tenant RAG system with internet search and RBAC",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(kb.router)
app.include_router(query.router)
app.include_router(query_stream.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Agentic RAG System API",
        "version": "1.0.0",
        "docs": "/docs",
        "environment": settings.environment
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "services": {
            "qdrant_url": settings.qdrant_url,
            "groq_configured": bool(settings.groq_api_key),
            "perplexity_configured": bool(settings.perplexity_api_key)
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )


