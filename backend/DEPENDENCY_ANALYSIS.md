# Dependency Analysis

## Unused Libraries

These are in `requirements.txt` but **NOT actually used**:

### 1. `pillow` ❌
- **Why it exists**: Used in `EmbeddingService.embed_image()` method
- **Why it's unused**: The `embed_image()` method is **never called** anywhere in the codebase
- **Impact**: Dead code for image embedding functionality

### 2. `pandas` ❓
- **Why it exists**: Used in `load_from_parquet.py`, `load_parquet_with_reembedding.py`, `reembed_and_load.py` scripts
- **Why it's not in workspace requirements**: The workshop uses `load_simple_wikipedia.py` which uses HuggingFace `datasets` library, NOT pandas
- **Note**: pandas might be pulled in as a dependency of `datasets`, but we don't explicitly need it

### 3. `torch` (implicit)
- **Why it exists**: Only imported inside `embed_image()` methods which are never called
- **Note**: Not in requirements.txt because `transformers` pulls it in as a dependency anyway

## Used Libraries - All Required

These ARE actually used:

- ✅ **fastapi, uvicorn** - Web framework
- ✅ **pydantic, pydantic-settings** - Data validation
- ✅ **python-multipart** - File upload handling
- ✅ **qdrant-client** - Vector database
- ✅ **groq** - LLM API client
- ✅ **httpx** - HTTP client for API calls
- ✅ **sentence-transformers** - Text embeddings (used actively)
- ✅ **transformers** - ML models (used via sentence-transformers)
- ✅ **pypdf2** - PDF parsing (fallback)
- ✅ **python-docx** - Word document parsing
- ✅ **pdfplumber** - PDF parsing (primary)
- ✅ **python-dotenv** - Environment variables
- ✅ **datasets** - HuggingFace datasets (for loading Wikipedia)
- ✅ **tqdm** - Progress bars in data loading scripts

## Recommendations

### For Workshop Setup
Keep all libraries EXCEPT pillow (already removed from `requirements-workshop.txt`)

### For Production
Could potentially remove:
- `pillow` - Definitely not needed
- `pandas` - If only using `load_simple_wikipedia.py` (HuggingFace datasets), pandas is a transitive dependency

The current `requirements-workshop.txt` is optimized and includes only what's needed.

