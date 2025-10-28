#!/usr/bin/env python3
"""
Simple RAG Demo - Understanding the Basics
============================================

This script shows the RAG process in the simplest way possible:
1. Store some text chunks in Qdrant
2. Search for similar chunks
3. Use those chunks to generate an answer

No classes, no complexity - just the basic flow.
"""

# Step 1: Setup - Load environment and connect to Qdrant
print("Step 1: Connecting to Qdrant...")
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))
load_dotenv(backend_path / ".env")

from app.core.config import settings
from qdrant_client import QdrantClient

# Connect to Qdrant
client = QdrantClient(
    url=settings.qdrant_url,
    api_key=settings.qdrant_api_key,
)
print(f"✓ Connected to {settings.qdrant_url}\n")


# Step 2: Prepare some sample documents to store
print("Step 2: Preparing sample documents...")
print("-" * 60)
documents = [
    {
        "id": "1",
        "text": "Python is a programming language. It is simple and readable.",
        "title": "Python Programming"
    },
    {
        "id": "2", 
        "text": "Machine learning uses algorithms to learn from data.",
        "title": "Machine Learning"
    },
    {
        "id": "3",
        "text": "Neural networks are inspired by how the human brain works.",
        "title": "Neural Networks"
    }
]
print(f"Created {len(documents)} sample documents")
print("Example: 'Python is a programming language...'\n")


# Step 3: Generate embeddings for these documents
print("Step 3: Converting text to vectors (embeddings)...")
print("-" * 60)
from sentence_transformers import SentenceTransformer

# Load the embedding model (one time setup - takes a few seconds)
print("Loading embedding model...")
model = SentenceTransformer("all-MiniLM-L6-v2")
print("✓ Model loaded")

# Convert each document's text to a vector
print("Generating embeddings...")
embeddings = []
for doc in documents:
    # This converts text to a 384-dimensional vector
    embedding = model.encode(doc["text"])
    embeddings.append(embedding)
    print(f"  ✓ '{doc['title']}' → {len(embedding)}-dim vector")

print(f"\n✓ All documents converted to vectors\n")


# Step 4: Store vectors in Qdrant
print("Step 4: Storing vectors in Qdrant...")
print("-" * 60)
collection_name = "simple_demo"

# Create collection if it doesn't exist
try:
    client.create_collection(
        collection_name,
        vectors_config={
            "size": 384,  # Dimension of our embeddings
            "distance": "Cosine"  # Use cosine similarity
        }
    )
    print(f"✓ Created collection '{collection_name}'")
except:
    print(f"✓ Collection '{collection_name}' already exists")

# Store the documents with their embeddings
points = []
for doc, embedding in zip(documents, embeddings):
    points.append({
        "id": doc["id"],
        "vector": embedding.tolist(),  # Convert numpy array to list
        "payload": {
            "text": doc["text"],
            "title": doc["title"]
        }
    })

client.upsert(collection_name=collection_name, points=points)
print(f"✓ Stored {len(points)} documents in Qdrant\n")


# Step 5: Now let's search!
print("Step 5: Searching for similar documents...")
print("-" * 60)
print("User asks: 'What is programming?'\n")

# Convert the query to an embedding (same process as documents)
query_text = "What is programming?"
query_embedding = model.encode(query_text).tolist()

print("1. Converted query to vector:")
print(f"   '{query_text}' → 384-dimensional vector\n")

# Search for similar vectors
print("2. Searching Qdrant for similar vectors...")
results = client.search(
    collection_name=collection_name,
    query_vector=query_embedding,
    limit=3  # Get top 3 most similar
)
print(f"   ✓ Found {len(results)} results\n")

# Show the results
print("3. Results ranked by similarity:")
for i, result in enumerate(results):
    print(f"   {i+1}. Score: {result.score:.3f} (higher = more similar)")
    print(f"      Title: {result.payload['title']}")
    print(f"      Text: {result.payload['text']}\n")


# Step 6: Use the results to generate an answer
print("Step 6: Generate answer using retrieved context...")
print("-" * 60)
print("This is where the LLM comes in:")
print(f"  Query: '{query_text}'")
print(f"  Context: Retrieved {len(results)} relevant documents")
print(f"  Answer: [LLM would generate answer here using the context]")
print("\n✓ This is the RAG process:")
print("  • RETRIEVE: Find relevant documents (Step 5)")
print("  • AUGMENT: Add those documents as context")
print("  • GENERATE: LLM creates answer using context")
print("\nThe magic of RAG is that the answer uses YOUR documents,")
print("not just the LLM's training data!\n")


# Summary
print("=" * 60)
print("SUMMARY: How RAG Works")
print("=" * 60)
print("""
1. STORAGE (Ingestion):
   Documents → Chunk → Embed → Store in Qdrant

2. QUERY (Retrieval):
   User Query → Embed → Search Qdrant → Get similar documents

3. GENERATION (Answer):
   Query + Retrieved Docs → LLM → Answer

Why it's powerful:
- LLM answers using YOUR data, not just training data
- Finds relevant info fast (vector search is very fast)
- Can handle documents that weren't in training data
- Semantic search understands meaning, not just keywords
""")

print("✓ Demo complete!")

