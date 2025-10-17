"""
Load Wikipedia data from local parquet file
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import pandas as pd
from tqdm import tqdm
from app.core.config import settings
from app.services.vector_store import MockVectorStore, QdrantVectorStore
import uuid
from datetime import datetime


async def load_from_parquet(parquet_path: str, num_articles: int = 100):
    """
    Load Wikipedia data from parquet file
    
    Args:
        parquet_path: Path to the parquet file
        num_articles: Number of articles to load
    """
    print("=" * 70)
    print("Loading Wikipedia from Local Parquet File")
    print("=" * 70)
    print(f"File: {parquet_path}")
    print(f"Articles to load: {num_articles}")
    print(f"Organization: {settings.org_id}")
    print(f"Mock mode: {settings.use_mock_vector_store}")
    print()
    
    # Initialize vector store
    print("[1/5] Initializing vector store...")
    if settings.use_mock_vector_store:
        vector_store = MockVectorStore()
        print("      ⚠️  Using MockVectorStore - data won't persist after restart!")
    else:
        vector_store = QdrantVectorStore(settings.qdrant_url, settings.qdrant_api_key)
        print(f"      ✓ Connected to Qdrant at {settings.qdrant_url}")
    print()
    
    # Load parquet file
    print("[2/5] Loading parquet file...")
    df = pd.read_parquet(parquet_path)
    print(f"      ✓ Loaded parquet with {len(df)} total articles")
    print(f"      Columns: {list(df.columns)}")
    
    # Limit to requested number
    df = df.head(num_articles)
    print(f"      ✓ Using first {len(df)} articles")
    print()
    
    # Create collections
    text_collection = f"{settings.org_id}_text"
    doc_collection = "documents"
    
    print("[3/5] Creating Qdrant collections...")
    # Determine embedding dimension from first article
    first_embedding = df.iloc[0]['embedding']
    embedding_dim = len(first_embedding)
    print(f"      Embedding dimension: {embedding_dim}")
    
    await vector_store.create_collection(text_collection, embedding_dim)
    await vector_store.create_collection(doc_collection, 384)  # Dummy collection
    print(f"      ✓ Text collection: {text_collection}")
    print(f"      ✓ Docs collection: {doc_collection}")
    print()
    
    # Process articles
    print("[4/5] Processing and uploading articles...")
    print(f"      ⚡ Using pre-computed embeddings (FAST!)")
    print()
    
    total_uploaded = 0
    failed_articles = []
    
    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Articles"):
        try:
            title = row.get("title", f"Article_{idx}")
            text = row.get("text", "")
            embedding = row.get("embedding", None)
            
            if not text or len(str(text).strip()) < 50:
                continue
            
            if embedding is None or len(embedding) == 0:
                continue
            
            # Generate document ID
            doc_id = str(uuid.uuid4())
            
            # Store the article with its pre-computed embedding
            # Use integer ID for Qdrant (more reliable)
            chunk_id = idx
            
            payload = {
                "doc_id": doc_id,
                "filename": f"{title}.txt",
                "content": str(text)[:2000],  # Store first 2000 chars
                "chunk_index": 0,
                "tags": ["wikipedia", "embedded"],
                "source": "local_parquet",
                "title": title
            }
            
            # Upload to vector store
            # Convert embedding to list if needed
            embedding_list = embedding if isinstance(embedding, list) else embedding.tolist()
            
            await vector_store.upsert_vectors(
                collection_name=text_collection,
                vectors=[embedding_list],
                payloads=[payload],
                ids=[chunk_id]
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
                    "tags": ["wikipedia", "embedded"],
                    "uploader_id": "system",
                    "size_bytes": len(str(text)),
                    "num_chunks": 1,
                    "source": "local_parquet",
                    "title": title
                }],
                ids=[doc_id]
            )
            
            total_uploaded += 1
            
        except Exception as e:
            failed_articles.append((idx, str(e)))
            continue
    
    print()
    print("[5/5] Summary")
    print("=" * 70)
    print("Dataset Loading Complete!")
    print("=" * 70)
    print(f"✓ Articles processed: {total_uploaded}")
    print(f"✓ Collection: {text_collection}")
    print(f"✓ Embedding dimension: {embedding_dim}")
    
    if failed_articles:
        print(f"⚠️  Failed articles: {len(failed_articles)}")
        if len(failed_articles) <= 5:
            for idx, err in failed_articles[:5]:
                print(f"    Article {idx}: {err}")
    
    print()
    print("=" * 70)
    print("Next Steps:")
    print("=" * 70)
    print("Test with a query:")
    print()
    print("curl -X POST http://localhost:8000/query/ \\")
    print("  -H 'Authorization: Bearer admin' \\")
    print("  -H 'Content-Type: application/json' \\")
    print("  -d '{\"query\":\"What is Python?\",\"mode\":\"local\",\"top_k\":3}'")
    print()
    
    if settings.use_mock_vector_store:
        print("=" * 70)
        print("⚠️  MockVectorStore Active - Data in Memory Only")
        print("=" * 70)
        print("Data will be LOST when backend restarts!")
        print("Keep backend running to query the data.")
        print("=" * 70)
    
    print()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Load Wikipedia from parquet file"
    )
    parser.add_argument(
        "--file",
        type=str,
        default="/Users/thierrydamiba/agent/train-00000-of-00001.parquet",
        help="Path to parquet file"
    )
    parser.add_argument(
        "--num-articles",
        type=int,
        default=100,
        help="Number of articles to load"
    )
    
    args = parser.parse_args()
    
    # Check file exists
    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}")
        sys.exit(1)
    
    # Run async function
    asyncio.run(load_from_parquet(args.file, args.num_articles))


if __name__ == "__main__":
    main()

