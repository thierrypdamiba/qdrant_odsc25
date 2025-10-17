"""
Load Wikipedia from parquet and RE-EMBED with our 384-dim model
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
import uuid
from datetime import datetime


async def load_and_reembed(parquet_path: str, num_articles: int = 100):
    """Load parquet and re-embed with 384-dim model"""
    
    print("=" * 70)
    print("Loading & Re-Embedding Wikipedia")
    print("=" * 70)
    print(f"File: {parquet_path}")
    print(f"Articles: {num_articles}")
    print(f"Target: {settings.qdrant_url}")
    print()
    
    # Initialize services
    print("[1/5] Initializing...")
    vector_store = QdrantVectorStore(settings.qdrant_url, settings.qdrant_api_key)
    embedding_service = EmbeddingService(settings.text_embedding_model)
    print(f"      ✓ Qdrant at {settings.qdrant_url}")
    print(f"      ✓ Embedding model: {settings.text_embedding_model} (384-dim)")
    print()
    
    # Load data
    print("[2/5] Loading parquet...")
    df = pd.read_parquet(parquet_path)
    df = df.head(num_articles)
    print(f"      ✓ Loaded {len(df)} articles")
    print()
    
    # Create collections
    print("[3/5] Creating collections...")
    text_collection = f"{settings.org_id}_text"
    doc_collection = "documents"
    
    # Delete and recreate to ensure clean slate
    try:
        await asyncio.sleep(0)  # Make async
        vector_store.client.delete_collection(text_collection)
        print(f"      ✓ Deleted old {text_collection}")
    except:
        pass
    
    await vector_store.create_collection(text_collection, 384)
    await vector_store.create_collection(doc_collection, 384)
    print(f"      ✓ Created {text_collection} (384-dim)")
    print()
    
    # Process and re-embed
    print("[4/5] Re-embedding with 384-dim model...")
    print("      This will take ~2-3 minutes for 100 articles")
    print()
    
    # Batch process for speed
    batch_size = 10
    total_uploaded = 0
    
    for batch_start in tqdm(range(0, len(df), batch_size), desc="Batches"):
        batch_df = df.iloc[batch_start:batch_start+batch_size]
        
        # Prepare texts for batch embedding
        texts = []
        metadata = []
        
        for idx, row in batch_df.iterrows():
            title = row.get("title", f"Article_{idx}")
            text = row.get("text", "")
            
            if not text or len(str(text).strip()) < 50:
                continue
            
            # Truncate to reasonable length for embedding
            text_str = str(text)[:2000]
            texts.append(text_str)
            metadata.append({
                "idx": idx,
                "title": title,
                "full_text": text_str,
                "doc_id": str(uuid.uuid4())
            })
        
        if not texts:
            continue
        
        # Batch embed
        embeddings = embedding_service.embed_text(texts)
        
        # Upload batch
        vectors = []
        payloads = []
        ids = []
        
        for meta, embedding in zip(metadata, embeddings):
            ids.append(meta["idx"])
            vectors.append(embedding)
            payloads.append({
                "doc_id": meta["doc_id"],
                "filename": f"{meta['title']}.txt",
                "content": meta["full_text"],
                "chunk_index": 0,
                "tags": ["wikipedia", "reembedded"],
                "source": "local_parquet",
                "title": meta["title"]
            })
        
        await vector_store.upsert_vectors(
            collection_name=text_collection,
            vectors=vectors,
            payloads=payloads,
            ids=ids
        )
        
        total_uploaded += len(vectors)
    
    print()
    print("[5/5] Summary")
    print("=" * 70)
    print("✓ Complete!")
    print("=" * 70)
    print(f"✓ Articles processed: {total_uploaded}")
    print(f"✓ Collection: {text_collection}")
    print(f"✓ Embedding dimension: 384 (matches query model!)")
    print()
    print("Test now:")
    print("  curl -X POST http://localhost:8000/query/ \\")
    print("    -H 'Authorization: Bearer admin' \\")
    print("    -H 'Content-Type: application/json' \\")
    print("    -d '{\"query\":\"What is Anarchism?\",\"mode\":\"local\",\"top_k\":3}'")
    print("=" * 70)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default="/Users/thierrydamiba/agent/train-00000-of-00001.parquet")
    parser.add_argument("--num-articles", type=int, default=100)
    args = parser.parse_args()
    
    asyncio.run(load_and_reembed(args.file, args.num_articles))

