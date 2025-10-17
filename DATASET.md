# Simple Wikipedia Dataset Integration

## Overview

The system now includes an optional **Simple Wikipedia dataset** loader that can populate your knowledge base with real content for testing and demonstration.

## Dataset Details

- **Source**: HuggingFace `pszemraj/simple_wikipedia`
- **Content**: Simplified English Wikipedia articles
- **Size**: ~1GB for 1000 articles
- **Processing time**: 5-10 minutes
- **Total chunks**: ~5,000-10,000 (depending on article length)

## Quick Start

### Load the Dataset (Default: 1000 articles)

```bash
./load-wikipedia.sh
```

### Load Custom Number of Articles

```bash
./load-wikipedia.sh 500   # Load 500 articles
./load-wikipedia.sh 2000  # Load 2000 articles
```

### What Happens

1. Downloads Simple Wikipedia from HuggingFace
2. Chunks each article (512 tokens, 50 overlap)
3. Generates embeddings using sentence-transformers
4. Uploads to Qdrant (`{org_id}_text` collection)
5. Stores metadata in `documents` collection

## Usage

Once loaded, you can query the dataset:

### Via Frontend
1. Go to http://localhost:3000/query
2. Select "Local (Knowledge Base)" mode
3. Ask questions like:
   - "What is machine learning?"
   - "Tell me about Python programming"
   - "Explain quantum computing"

### Via API
```bash
curl -X POST http://localhost:8000/query/ \
  -H "Authorization: Bearer admin" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is artificial intelligence?",
    "mode": "local",
    "top_k": 5
  }'
```

## Manual Loading (Advanced)

```bash
cd backend
source venv/bin/activate
python scripts/load_simple_wikipedia.py --num-articles 1000
```

## Dataset Structure

Each article becomes:
- **1 document** in `documents` collection
- **Multiple chunks** in `{org_id}_text` collection
- Tagged with: `["wikipedia", "simple_wikipedia"]`

### Chunk Example
```json
{
  "doc_id": "uuid",
  "filename": "Article Title.txt",
  "content": "Article text chunk...",
  "chunk_index": 0,
  "tags": ["wikipedia", "simple_wikipedia"],
  "source": "simple_wikipedia"
}
```

### Document Metadata Example
```json
{
  "doc_id": "uuid",
  "filename": "Article Title.txt",
  "title": "Article Title",
  "file_type": "txt",
  "upload_date": "2025-01-01T00:00:00",
  "status": "completed",
  "tags": ["wikipedia", "simple_wikipedia"],
  "uploader_id": "system",
  "size_bytes": 12345,
  "num_chunks": 42,
  "source": "simple_wikipedia"
}
```

## Storage Requirements

| Articles | Approx Size | Chunks |
|----------|-------------|---------|
| 100 | ~100MB | ~1,000 |
| 500 | ~500MB | ~5,000 |
| 1000 | ~1GB | ~10,000 |
| 2000 | ~2GB | ~20,000 |

## Important Notes

### Mock Mode Warning
If you're running with `USE_MOCK_VECTOR_STORE=true`:
- ⚠️ **Data will be lost when backend restarts!**
- The dataset loads to memory only
- Switch to real Qdrant for persistence

### Using Real Qdrant

1. **Start Qdrant**:
```bash
docker-compose up -d
```

2. **Update `.env`**:
```bash
USE_MOCK_VECTOR_STORE=false
QDRANT_URL=http://localhost:6333
```

3. **Load dataset**:
```bash
./load-wikipedia.sh
```

Now data persists across restarts!

## Performance Tips

### First Run (Cold Start)
- Downloads dataset: ~2-3 minutes
- Processes & uploads: ~5-10 minutes
- **Total**: ~7-13 minutes

### Subsequent Runs
- Dataset cached locally
- Only processing time: ~5-10 minutes

### Speed Up Loading
```python
# Reduce number of articles
./load-wikipedia.sh 100  # Much faster for testing

# Or edit the script to:
# - Reduce chunk size
# - Skip embedding generation (use dummy vectors)
# - Batch upload in larger groups
```

## Troubleshooting

### "datasets not found"
```bash
cd backend
source venv/bin/activate
pip install datasets tqdm
```

### "Qdrant connection refused"
Make sure Qdrant is running:
```bash
docker-compose up -d
# Or check QDRANT_URL in .env
```

### "Out of memory"
- Reduce number of articles: `./load-wikipedia.sh 100`
- Close other applications
- Or use a machine with more RAM

### Loading Stuck
- Check your internet connection
- First download can take time (~1GB)
- Dataset is cached in `~/.cache/huggingface/datasets`

## Alternative Datasets

Want to try other datasets? Edit `scripts/load_simple_wikipedia.py`:

### Wikipedia (Full, English)
```python
dataset = load_dataset("wikipedia", "20220301.en", split="train[:1000]")
```

### SQuAD (Q&A)
```python
dataset = load_dataset("squad", split="train[:1000]")
# Adjust processing for context field
```

### Natural Questions
```python
dataset = load_dataset("natural_questions", split="train[:1000]")
```

## Clearing the Dataset

To remove all Wikipedia articles:

### Via API
```bash
# Delete all documents with wikipedia tag
# (Not implemented yet - manual approach below)
```

### Manual (Qdrant)
1. Open Qdrant dashboard: http://localhost:6333/dashboard
2. Delete collections: `{org_id}_text` and `documents`
3. Restart backend (collections will be recreated)

### Or restart from scratch
```bash
docker-compose down -v  # Removes Qdrant data
docker-compose up -d     # Fresh start
```

## Testing the Dataset

### Sample Questions
After loading, try these queries:

**Science:**
- "Explain gravity"
- "What is DNA?"
- "How does photosynthesis work?"

**Technology:**
- "What is Python?"
- "Explain the internet"
- "What is artificial intelligence?"

**History:**
- "Who was Albert Einstein?"
- "Tell me about World War 2"
- "What is the Renaissance?"

**General:**
- "What is mathematics?"
- "Explain democracy"
- "What are the planets?"

## Example Output

```bash
$ ./load-wikipedia.sh 100

Loading Simple Wikipedia Dataset
================================

Initializing services...
✓ Connected to Qdrant at http://localhost:6333
✓ Embedding service initialized

Downloading Simple Wikipedia dataset...
✓ Loaded 100 articles

Creating Qdrant collections...
✓ Collections created: default_org_text, documents

Processing and uploading articles...
Articles: 100%|████████████| 100/100 [05:23<00:00,  3.23s/it]

======================================================================
Dataset Loading Complete!
======================================================================
✓ Articles processed: 100
✓ Total chunks created: 1,247
✓ Collection: default_org_text

You can now query these articles using:
  - Frontend: http://localhost:3000/query
  - API: POST http://localhost:8000/query/

======================================================================
```

## Benefits

✅ **Instant Knowledge Base**: No need to manually upload documents
✅ **Real Content**: Test with actual Wikipedia articles
✅ **Varied Topics**: Wide range of subjects for testing
✅ **Quality Data**: Well-written, structured content
✅ **Easy Updates**: Re-run script to refresh or add more articles

---

**Ready to load?** Run `./load-wikipedia.sh` and you'll have a populated knowledge base in ~10 minutes!


