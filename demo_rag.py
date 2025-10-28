#!/usr/bin/env python3
"""
RAG System Demo Script
=======================

OVERVIEW:
This script demonstrates the complete RAG (Retrieval-Augmented Generation) pipeline
by walking through each component step-by-step.

ARCHITECTURE:
┌─────────────┐
│  Documents  │  Upload PDFs, DOCX, TXT files
└─────┬───────┘
      │ Extract text
      ▼
┌─────────────┐
│   Chunker   │  Split into 512-word chunks with 50-word overlap
└─────┬───────┘
      │ Chunk text
      ▼
┌─────────────┐
│  Embedding  │  Convert text to 384-dimensional vectors (all-MiniLM-L6-v2)
└─────┬───────┘
      │ Store vectors + metadata
      ▼
┌─────────────┐
│   Qdrant    │  Vector database for fast similarity search
└─────┬───────┘
      │ Query embedding
      ▼
┌─────────────┐
│   Search    │  Find top-k most similar chunks (cosine similarity)
└─────┬───────┘
      │ Retrieved chunks
      ▼
┌─────────────┐
│     LLM     │  Generate answer using retrieved context (Groq)
└─────────────┘

THIS SCRIPT DEMONSTRATES:
1. Document Processing: How text is chunked for better retrieval
2. Embedding Generation: Converting text to numerical vectors
3. Vector Storage: Storing embeddings in Qdrant Cloud
4. Semantic Search: Finding similar content based on meaning
5. RAG Query: Combining retrieval with LLM generation
6. Internet Search: Real-time web search (Perplexity API)
7. Hybrid Search: Combining local + internet results

Run this script to understand each step of the RAG pipeline.
"""

import os
import sys
import asyncio
import time
from typing import List, Dict, Any
from pathlib import Path

# Add the backend directory to Python path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

# Load environment variables from backend/.env
from dotenv import load_dotenv
load_dotenv(backend_path / ".env")

from app.core.config import settings
from app.services.vector_store import QdrantVectorStore
from app.services.document_processor import DocumentProcessor, EmbeddingService
from app.services.rag import RAGService
from app.services.llm import GroqLLMService
from app.services.search import PerplexitySearchService


class RAGDemo:
    """Demo class to showcase RAG functionality"""
    
    def __init__(self):
        self.vector_store = None
        self.embedding_service = None
        self.rag_service = None
        self.llm_service = None
        self.search_service = None
        
    async def setup_services(self):
        """Initialize all services"""
        print("🔧 Setting up services...")
        
        # Initialize vector store (Qdrant Cloud)
        self.vector_store = QdrantVectorStore(
            settings.qdrant_url, 
            settings.qdrant_api_key,
            cloud_inference=settings.qdrant_cloud_inference
        )
        print(f"   ✓ Vector store connected to {settings.qdrant_url}")
        
        # Initialize embedding service
        self.embedding_service = EmbeddingService(
            settings.text_embedding_model,
            settings.image_embedding_model
        )
        print(f"   ✓ Embedding service loaded ({settings.text_embedding_model})")
        
        # Initialize LLM service
        if not settings.groq_api_key:
            raise Exception("GROQ_API_KEY is required. Please set it in your .env file.")
        self.llm_service = GroqLLMService(settings.groq_api_key)
        print(f"   ✓ LLM service initialized (Groq)")
        
        # Initialize search service
        if not settings.perplexity_api_key:
            raise Exception("PERPLEXITY_API_KEY is required. Please set it in your .env file.")
        self.search_service = PerplexitySearchService(settings.perplexity_api_key)
        print(f"   ✓ Search service initialized (Perplexity)")
        
        # Initialize RAG service
        self.rag_service = RAGService(
            self.vector_store,
            self.llm_service,
            self.search_service,
            self.embedding_service
        )
        print(f"   ✓ RAG service ready")
        
    async def demo_document_processing(self):
        """Demonstrate document processing and chunking
        
        This function shows how the RAG system processes text documents:
        1. Takes raw text content
        2. Splits it into smaller chunks (typically 512 words)
        3. Chunks overlap by a few words (50 by default) for context continuity
        
        Why chunking?
        - LLMs have token limits (usually 4k-32k tokens)
        - Semantic search works better with focused text segments
        - Allows retrieval of specific relevant sections
        - Enables parallel processing of chunks
        """
        print("\n📄 Document Processing Demo")
        print("=" * 50)
        
        # Sample document text about AI/ML for demonstration
        # In a real application, this would come from uploaded PDFs, DOCX files, etc.
        sample_text = """
        Artificial Intelligence (AI) is a branch of computer science that aims to create 
        intelligent machines that can perform tasks that typically require human intelligence. 
        These tasks include learning, reasoning, problem-solving, perception, and language understanding.
        
        Machine Learning is a subset of AI that focuses on algorithms that can learn from data 
        without being explicitly programmed. Deep Learning is a subset of machine learning 
        that uses neural networks with multiple layers to model and understand complex patterns.
        
        Natural Language Processing (NLP) is another important area of AI that deals with 
        the interaction between computers and humans through natural language. It enables 
        computers to understand, interpret, and generate human language in a valuable way.
        
        Computer Vision is the field of AI that trains computers to interpret and understand 
        the visual world. Using digital images from cameras and videos and deep learning models, 
        machines can accurately identify and classify objects.
        """
        
        # Initialize document processor
        # This class handles text extraction, chunking, and metadata creation
        doc_processor = DocumentProcessor()
        
        print(f"Original text length: {len(sample_text)} characters")
        
        # Chunk the text into smaller pieces
        # chunk_size: Number of words per chunk (default: 512 words)
        # overlap: Number of overlapping words between chunks (default: 50 words)
        # Overlap ensures context continuity when retrieving adjacent chunks
        chunks = doc_processor.chunk_text(
            sample_text,
            chunk_size=settings.chunk_size,      # 512 words per chunk
            overlap=settings.chunk_overlap         # 50 words overlap
        )
        
        print(f"Number of chunks created: {len(chunks)}")
        
        for i, chunk in enumerate(chunks):
            print(f"\nChunk {i+1}:")
            print(f"  Length: {len(chunk['text'])} characters")
            print(f"  Preview: {chunk['text'][:100]}...")
            
        return chunks
        
    async def demo_embedding_generation(self, chunks: List[Dict]):
        """Demonstrate embedding generation
        
        Embeddings are numerical representations of text that capture semantic meaning.
        - Each chunk of text is converted to a vector (list of numbers)
        - Similar texts have similar vectors (measured by cosine similarity)
        - Uses pre-trained models like all-MiniLM-L6-v2 (384 dimensions)
        - Generated embeddings are stored for fast similarity search later
        """
        print("\n🧠 Embedding Generation Demo")
        print("=" * 50)
        
        # Extract just the text content from chunks
        # This prepares the input for the embedding model
        chunk_texts = [chunk["text"] for chunk in chunks]
        
        print(f"Generating embeddings for {len(chunk_texts)} chunks...")
        print("(This converts text to numerical vectors that capture semantic meaning)")
        start_time = time.time()
        
        # Generate embeddings using SentenceTransformer model
        # This converts each text chunk into a 384-dimensional vector
        # Similar texts will have similar vectors (measured by cosine similarity)
        embeddings = self.embedding_service.embed_text(chunk_texts)
        
        end_time = time.time()
        print(f"✓ Generated {len(embeddings)} embeddings in {end_time - start_time:.2f} seconds")
        print(f"✓ Embedding dimension: {len(embeddings[0])}")  # 384 dimensions
        print(f"✓ Model used: {settings.text_embedding_model}")
        print("  (This model understands semantic meaning, not just keywords)")
        
        return embeddings
        
    async def demo_vector_storage(self, chunks: List[Dict], embeddings: List[List[float]]):
        """Demonstrate vector storage in Qdrant
        
        Qdrant is a vector database optimized for similarity search:
        - Stores embeddings with metadata (content, tags, etc.)
        - Enables fast similarity search using cosine distance
        - Supports filtering and complex queries
        - Cloud inference can generate embeddings server-side
        """
        print("\n🗄️ Vector Storage Demo")
        print("=" * 50)
        
        # Collection names are namespaced by organization
        # Format: {org_id}_{collection_type}
        # e.g., "default_org_text" for text chunks
        collection_name = f"{settings.org_id}_demo"
        
        # Create a new collection in Qdrant
        # This is like creating a new table in a relational database
        print(f"Creating collection: {collection_name}")
        print(f"  Vector dimension: {len(embeddings[0])} (384 for all-MiniLM-L6-v2)")
        await self.vector_store.create_collection(collection_name, len(embeddings[0]))
        
        # Prepare data for storage in Qdrant
        # Each point in Qdrant consists of:
        # - id: Unique identifier (UUID for cloud inference)
        # - vector: The embedding (numerical representation)
        # - payload: Metadata (text, tags, source, etc.)
        payloads = []
        ids = []
        texts = []
        
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            import uuid
            # Cloud inference requires UUID format, not string IDs
            chunk_id = str(uuid.uuid4())
            ids.append(chunk_id)
            texts.append(chunk["text"])
            
            # Payload contains metadata associated with the vector
            # This metadata is returned with search results
            payloads.append({
                "doc_id": "demo_doc_1",              # Document identifier
                "filename": "ai_introduction.txt",   # Source file
                "content": chunk["text"],            # Full text content
                "chunk_index": i,                     # Position in document
                "tags": ["demo", "ai", "introduction"], # For filtering
                "source": "demo_script"                # Where it came from
            })
        
        # Store in vector database
        print(f"Storing {len(embeddings)} vectors in Qdrant...")
        start_time = time.time()
        
        await self.vector_store.upsert_vectors(
            collection_name=collection_name,
            vectors=embeddings,
            payloads=payloads,
            ids=ids
        )
        
        end_time = time.time()
        print(f"✓ Stored vectors in {end_time - start_time:.2f} seconds")
        
        return collection_name
        
    async def demo_semantic_search(self, collection_name: str):
        """Demonstrate semantic search
        
        Semantic search finds documents based on meaning, not keywords:
        - Query is converted to the same embedding space as stored chunks
        - Cosine similarity is used to find the closest vectors
        - Results are ranked by relevance (higher score = more relevant)
        - Much faster than keyword search and understands synonyms, context
        """
        print("\n🔍 Semantic Search Demo")
        print("=" * 50)
        print("Searching for similar content based on meaning (not just keywords)")
        
        # Test queries that should find relevant content
        queries = [
            "What is machine learning?",
            "How does computer vision work?",
            "Explain natural language processing",
            "What are neural networks?"
        ]
        
        for query in queries:
            print(f"\nQuery: '{query}'")
            
            # Generate query embedding
            # This converts the search query into the same 384-dimensional vector space
            # Now we can find semantically similar chunks using vector similarity
            query_embedding = self.embedding_service.embed_text_query(query)
            
            # Search for similar chunks using cosine similarity
            # Qdrant compares the query vector against all stored vectors
            # Returns top_k most similar chunks based on cosine distance
            start_time = time.time()
            results = await self.vector_store.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                top_k=3  # Return top 3 most similar chunks
            )
            search_time = time.time() - start_time
            
            print(f"  Search time: {search_time:.3f} seconds")
            print(f"  Found {len(results)} results:")
            
            for i, result in enumerate(results):
                score = result["score"]
                content = result["payload"]["content"]
                print(f"    {i+1}. Score: {score:.3f}")
                print(f"       Content: {content[:80]}...")
                
    async def demo_rag_query(self):
        """Demonstrate RAG query processing
        
        RAG (Retrieval-Augmented Generation) combines:
        1. RETRIEVAL: Find relevant chunks from vector database
        2. AUGMENTATION: Add those chunks as context to the prompt
        3. GENERATION: LLM generates answer using the retrieved context
        
        This gives accurate, up-to-date answers based on your documents.
        """
        print("\n🤖 RAG Query Demo")
        print("=" * 50)
        print("RAG combines retrieval + generation for accurate answers")
        
        # Test queries that require understanding multiple concepts
        queries = [
            "What is artificial intelligence?",
            "How does machine learning work?",
            "What is the difference between AI and ML?"
        ]
        
        for query in queries:
            print(f"\nQuery: '{query}'")
            print("Pipeline: Embed → Search → Retrieve → Generate")
            
            # Process query through complete RAG pipeline:
            # 1. Embed the query
            # 2. Search for similar chunks
            # 3. Retrieve top_k chunks
            # 4. Pass chunks + query to LLM
            # 5. LLM generates answer based on retrieved context
            start_time = time.time()
            result = await self.rag_service.query_local(
                query=query,
                top_k=3,  # Retrieve 3 most relevant chunks
                return_timing=True  # Get performance metrics
            )
            total_time = time.time() - start_time
            
            print(f"  Total processing time: {total_time:.2f} seconds")
            
            # Breakdown of where time is spent
            if "timings" in result:
                timings = result["timings"]
                print(f"  - Embedding query: {timings.get('embedding_ms', 0)}ms")
                print(f"  - Vector search: {timings.get('qdrant_search_ms', 0)}ms")
                print(f"  - LLM generation: {timings.get('llm_generation_ms', 0)}ms")
                print("  → Most time is spent in LLM generation (Groq API call)")
            
            print(f"  Answer: {result['answer'][:200]}...")
            print(f"  Sources: {len(result['sources'])}")
            
            for i, source in enumerate(result['sources'][:2]):
                print(f"    {i+1}. {source.doc_name} (score: {source.score:.3f})")
                
    async def demo_internet_search(self):
        """Demonstrate internet search functionality
        
        Internet search uses Perplexity API to search the web:
        - Gets real-time information from the internet
        - Useful for current events, latest news, recent developments
        - Complements local RAG with up-to-date information
        - Slower than local search (requires internet API call)
        """
        print("\n🌐 Internet Search Demo")
        print("=" * 50)
        print("Searching the internet for real-time information (Perplexity API)")
        
        # Query that needs current information not in our documents
        query = "What are the latest developments in AI?"
        print(f"Query: '{query}'")
        
        try:
            start_time = time.time()
            result = await self.rag_service.query_internet(query, num_results=3)
            search_time = time.time() - start_time
            
            print(f"Search time: {search_time:.2f} seconds")
            print(f"Answer: {result['answer'][:200]}...")
            print(f"Sources: {len(result['sources'])}")
            
            for i, source in enumerate(result['sources']):
                print(f"  {i+1}. {source.doc_name}")
                print(f"     URL: {source.doc_id}")
                
        except Exception as e:
            print(f"Internet search failed: {e}")
            print("This might be due to missing Perplexity API key or network issues")
            
    async def demo_hybrid_search(self):
        """Demonstrate hybrid search (local + internet)"""
        print("\n🔄 Hybrid Search Demo")
        print("=" * 50)
        
        query = "What is the current state of artificial intelligence?"
        print(f"Query: '{query}'")
        
        try:
            start_time = time.time()
            result = await self.rag_service.query_hybrid(query, top_k=3)
            total_time = time.time() - start_time
            
            print(f"Total time: {total_time:.2f} seconds")
            print(f"Answer: {result['answer'][:200]}...")
            print(f"Total sources: {len(result['sources'])}")
            
            # Count local vs internet sources
            local_sources = [s for s in result['sources'] if 'simple_wikipedia' in s.doc_name or 'demo' in s.doc_name]
            internet_sources = [s for s in result['sources'] if s.doc_name == 'Perplexity AI - Real-time Search']
            
            print(f"  - Local sources: {len(local_sources)}")
            print(f"  - Internet sources: {len(internet_sources)}")
            
        except Exception as e:
            print(f"Hybrid search failed: {e}")
            print("This might be due to missing API keys or network issues")
            
    async def cleanup_demo_data(self, collection_name: str):
        """Clean up demo data"""
        print("\n🧹 Cleanup")
        print("=" * 50)
        
        try:
            # Note: In a real scenario, you might want to delete the collection
            # For demo purposes, we'll just mention it
            print(f"Demo collection '{collection_name}' created successfully")
            print("In production, you might want to delete demo collections after testing")
            
        except Exception as e:
            print(f"Cleanup note: {e}")
            
    async def run_full_demo(self):
        """Run the complete RAG demo"""
        print("🚀 RAG System Demo")
        print("=" * 60)
        print("This demo showcases the core functionality of the Agentic RAG system")
        print("=" * 60)
        
        try:
            # Setup
            await self.setup_services()
            
            # Document processing
            chunks = await self.demo_document_processing()
            
            # Embedding generation
            embeddings = await self.demo_embedding_generation(chunks)
            
            # Vector storage
            collection_name = await self.demo_vector_storage(chunks, embeddings)
            
            # Semantic search
            await self.demo_semantic_search(collection_name)
            
            # RAG query
            await self.demo_rag_query()
            
            # Internet search
            await self.demo_internet_search()
            
            # Hybrid search
            await self.demo_hybrid_search()
            
            # Cleanup
            await self.cleanup_demo_data(collection_name)
            
            print("\n✅ Demo completed successfully!")
            print("\nKey takeaways:")
            print("- Document chunking breaks text into manageable pieces")
            print("- Embeddings convert text to numerical vectors for similarity search")
            print("- Vector databases enable fast semantic search")
            print("- RAG combines retrieval with generation for accurate answers")
            print("- Hybrid search combines local knowledge with internet information")
            
        except Exception as e:
            print(f"\n❌ Demo failed: {e}")
            print("Make sure you have:")
            print("1. Set up your .env file with API keys")
            print("2. Installed all dependencies")
            print("3. Have internet connectivity")
            print("4. Qdrant cluster is accessible")


def main():
    """Main entry point"""
    print("RAG System Demo Script")
    print("=" * 30)
    
    # Check if .env file exists
    env_file = Path("backend/.env")
    if not env_file.exists():
        print("❌ Error: backend/.env file not found!")
        print("Please create the .env file with your API keys first.")
        print("See WORKSHOP_SETUP.md for instructions.")
        return
    
    # Check if we're in the right directory
    if not Path("backend").exists():
        print("❌ Error: backend directory not found!")
        print("Please run this script from the project root directory.")
        return
    
    # Run the demo
    demo = RAGDemo()
    asyncio.run(demo.run_full_demo())


if __name__ == "__main__":
    main()
