"""
Re-embed parquet data with 384-dim model and load to Qdrant
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import pandas as pd
from tqdm import tqdm
from app.core.config import settings
from app.services.vector_store import QdrantVectorStore
from app.services.document_processor import EmbeddingService
from datetime import datetime


async def reembed_and_load(parquet_path: str, num_articles: int = 100):
    """Re-embed and load Wikipedia data"""
    print("=" * 70)
    print("Re-embedding and Loading Wikipedia to Qdrant")
    print("=" * 70)
    print(f"File: {parquet_path}")
    print(f"Articles: {num_articles}")
    print(f"Target dimension: 384 (all-MiniLM-L6-v2)")
    print()
    
    # Load parquet
    print("[1/4] Loading parquet...")
    df = pd.read_parquet(parquet_path).head(num_articles)
    print(f"      ✓ Loaded {len(df)} articles")
    print()
    
    # Initialize services
    print("[2/4] Initializing services...")
    vector_store = QdrantVectorStore("http://localhost:6333", None)
    embedding_service = EmbeddingService()
    print("      ✓ Qdrant connected")
    print("      ✓ Embedding model loaded")
    print()
    
    # Create collection
    print("[3/4] Creating collection...")
    collection_name = f"{settings.org_id}_text"
    try:
        await vector_store.create_collection(collection_name, 384)
        print(f"      ✓ Collection: {collection_name}")
    except:
        print(f"      ✓ Collection already exists: {collection_name}")
    print()
    
    # Process articles
    print("[4/4] Re-embedding and uploading...")
    print("      This may take 2-3 minutes for 100 articles...")
    print()
    
    # Batch process for speed
    batch_size = 10
    total_loaded = 0
    
    for i in tqdm(range(0, len(df), batch_size), desc="Batches"):
        batch = df.iloc[i:i+batch_size]
        
        # Extract texts
        texts = [str(row['text'])[:1000] for idx, row in batch.iterrows()]  # First 1000 chars
        titles = [str(row['title']) for idx, row in batch.iterrows()]
        
        # Generate embeddings
        embeddings = embedding_service.embed_text(texts)
        
        # Prepare data
        ids = list(range(i, i+len(batch)))
        payloads = []
        
        for j, (idx, row) in enumerate(batch.iterrows()):
            payloads.append({
                "doc_id": f"doc_{i+j}",
                "filename": f"{titles[j]}.txt",
                "content": texts[j],
                "chunk_index": 0,
                "tags": ["wikipedia", "re-embedded"],
                "source": "parquet_reembedded",
                "title": titles[j]
            })
        
        # Upload batch
        await vector_store.upsert_vectors(
            collection_name=collection_name,
            vectors=embeddings,
            payloads=payloads,
            ids=ids
        )
        
        total_loaded += len(batch)
    
    print()
    print("=" * 70)
    print("Complete!")
    print("=" * 70)
    print(f"✓ Articles loaded: {total_loaded}")
    print(f"✓ Collection: {collection_name}")
    print(f"✓ Embedding dimension: 384")
    print()
    print("Ready to query! Backend should now return real results.")
    print("=" * 70)


async def main():
    await reembed_and_load(
        "/Users/thierrydamiba/agent/train-00000-of-00001.parquet",
        100
    )


if __name__ == "__main__":
    asyncio.run(main())

