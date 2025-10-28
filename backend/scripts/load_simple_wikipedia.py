"""
Script to load Simple Wikipedia dataset from HuggingFace into Qdrant
Dataset: pszemraj/simple_wikipedia
"""
import sys
import os
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from datasets import load_dataset
from tqdm import tqdm
from app.core.config import settings
from app.services.vector_store import QdrantVectorStore
from app.services.document_processor import EmbeddingService
import uuid
from datetime import datetime


async def load_simple_wikipedia(num_articles: int = 1000):
    """
    Load Simple Wikipedia articles into Qdrant
    
    Args:
        num_articles: Number of articles to load (default: 1000)
    """
    print("=" * 70)
    print("Loading Simple Wikipedia into Qdrant")
    print("=" * 70)
    print(f"Number of articles: {num_articles}")
    print(f"Organization: {settings.org_id}")
    print(f"Mock mode: {settings.use_mock_vector_store}")
    print()
    
    # Initialize services
    print("[1/6] Initializing services...")
    if settings.use_mock_vector_store:
        # Mock store not implemented - use Qdrant instead
        print("      ⚠️  Mock store requested but not implemented, using Qdrant!")
    
    vector_store = QdrantVectorStore(
        settings.qdrant_url, 
        settings.qdrant_api_key,
        cloud_inference=settings.qdrant_cloud_inference
    )
    print(f"      ✓ Connected to Qdrant at {settings.qdrant_url}")
    
    print("[2/6] Loading embedding models...")
    embedding_service = EmbeddingService(
        settings.text_embedding_model,
        settings.image_embedding_model
    )
    print(f"      ✓ Text model: {settings.text_embedding_model}")
    print()
    
    # Load dataset
    print("[3/6] Downloading Wikipedia dataset from HuggingFace...")
    print(f"      Dataset: not-lain/wikipedia-small-3000-embedded")
    print(f"      Articles: {num_articles} (max 3000 available)")
    print(f"      ⚡ This dataset has pre-computed embeddings (MUCH faster!)")
    print(f"      (First download may take 1-2 minutes, then cached)")
    print()
    # Load dataset - Wikipedia with pre-computed embeddings
    full_dataset = load_dataset("not-lain/wikipedia-small-3000-embedded")
    dataset = full_dataset["train"].select(range(min(num_articles, len(full_dataset["train"]))))
    print(f"      ✓ Loaded {len(dataset)} articles from HuggingFace")
    print()
    
    # Create collections
    text_collection = f"{settings.org_id}_text"
    doc_collection = "documents"
    
    print("[4/6] Creating Qdrant collections...")
    # Use 384-dimensional embeddings (matching the embedding service)
    embedding_dim = 384
    print(f"      Embedding dimension: {embedding_dim}")
    
    await vector_store.create_collection(text_collection, embedding_dim)
    await vector_store.create_collection(doc_collection, embedding_dim)
    print(f"      ✓ Text collection: {text_collection}")
    print(f"      ✓ Docs collection: {doc_collection}")
    print()
    
    # Process articles
    print("[5/6] Processing and uploading articles...")
    print(f"      This will take ~2-5 minutes for {num_articles} articles")
    print(f"      Progress bar will show below:")
    print()
    
    total_chunks = 0
    failed_articles = []
    
    for idx, article in enumerate(tqdm(dataset, desc="Articles")):
        try:
            # Extract article data - this dataset has pre-computed embeddings!
            title = article.get("title", f"Article_{idx}")
            text = article.get("text", "")
            embedding = article.get("embedding", None)  # Pre-computed!
            
            if not text or len(text.strip()) < 50:
                continue
            
            # Generate document ID
            doc_id = str(uuid.uuid4())
            
            # Chunk the text
            words = text.split()
            chunk_size = settings.chunk_size
            overlap = settings.chunk_overlap
            
            chunks = []
            for i in range(0, len(words), chunk_size - overlap):
                chunk_words = words[i:i + chunk_size]
                chunk_text = " ".join(chunk_words)
                
                if len(chunk_text.strip()) > 20:
                    chunks.append({
                        "text": chunk_text,
                        "chunk_index": len(chunks)
                    })
            
            if not chunks:
                continue
            
            # Prepare payloads
            payloads = []
            ids = []
            texts = []
            for chunk in chunks:
                # Use UUID for point ID (required by cloud inference)
                chunk_id = str(uuid.uuid4())
                ids.append(chunk_id)
                texts.append(chunk["text"])
                payloads.append({
                    "doc_id": doc_id,
                    "filename": f"{title}.txt",
                    "content": chunk["text"],
                    "chunk_index": chunk["chunk_index"],
                    "tags": ["wikipedia", "simple_wikipedia"],
                    "source": "simple_wikipedia"
                })
            
            # Upload chunks to vector store with cloud inference (pass texts, not vectors)
            await vector_store.upsert_vectors(
                collection_name=text_collection,
                vectors=None,  # Will be generated by cloud inference
                payloads=payloads,
                ids=ids,
                texts=texts  # Pass texts for cloud embedding
            )
            
            # Store document metadata
            await vector_store.upsert_vectors(
                collection_name=doc_collection,
                vectors=[[0.0] * 384],  # Dummy vector
                payloads=[{
                    "doc_id": doc_id,
                    "filename": f"{title}.txt",
                    "file_type": "txt",
                    "upload_date": datetime.utcnow().isoformat(),
                    "status": "completed",
                    "tags": ["wikipedia", "simple_wikipedia"],
                    "uploader_id": "system",
                    "size_bytes": len(text),
                    "num_chunks": len(chunks),
                    "source": "simple_wikipedia",
                    "title": title
                }],
                ids=[doc_id]
            )
            
            total_chunks += len(chunks)
            
        except Exception as e:
            failed_articles.append((idx, str(e)))
            continue
    
    print()
    print("[6/6] Summary")
    print("=" * 70)
    print("Dataset Loading Complete!")
    print("=" * 70)
    print(f"✓ Articles processed: {len(dataset) - len(failed_articles)}")
    print(f"✓ Total chunks created: {total_chunks}")
    print(f"✓ Average chunks per article: {total_chunks / max(len(dataset) - len(failed_articles), 1):.1f}")
    print(f"✓ Collection: {text_collection}")
    
    if failed_articles:
        print(f"⚠️  Failed articles: {len(failed_articles)}")
        if len(failed_articles) <= 5:
            for idx, err in failed_articles:
                print(f"    Article {idx}: {err}")
    
    print()
    print("=" * 70)
    print("Next Steps:")
    print("=" * 70)
    print("1. Make sure backend is running:")
    print("   ./start-backend.sh")
    print()
    print("2. Query via Frontend:")
    print("   http://localhost:3000/query")
    print("   Try: 'What is Python?', 'Explain gravity', 'Tell me about Mars'")
    print()
    print("3. Query via API:")
    print("   curl -X POST http://localhost:8000/query/ \\")
    print("     -H 'Authorization: Bearer admin' \\")
    print("     -H 'Content-Type: application/json' \\")
    print("     -d '{\"query\":\"What is Python?\",\"mode\":\"local\",\"top_k\":3}'")
    print()
    
    if settings.use_mock_vector_store:
        print("=" * 70)
        print("⚠️  IMPORTANT: MockVectorStore Active")
        print("=" * 70)
        print("Data is stored IN MEMORY and will be LOST when backend restarts!")
        print()
        print("To persist data:")
        print("1. Start Qdrant: docker-compose up -d")
        print("2. Update backend/.env: USE_MOCK_VECTOR_STORE=false")
        print("3. Restart backend and re-run this script")
        print("=" * 70)
    else:
        print("✓ Data persisted in Qdrant - will survive backend restarts")
    
    print()
    print("=" * 70)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Load Simple Wikipedia into Qdrant"
    )
    parser.add_argument(
        "--num-articles",
        type=int,
        default=1000,
        help="Number of articles to load (default: 1000)"
    )
    
    args = parser.parse_args()
    
    # Run async function
    asyncio.run(load_simple_wikipedia(args.num_articles))


if __name__ == "__main__":
    main()

