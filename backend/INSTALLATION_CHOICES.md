# Installation Choices - Cloud Inference vs Local Embeddings

## Quick Decision Guide

**Use Cloud Inference** (Recommended for Workshop):
- ✅ Faster setup (~2-3 minutes)
- ✅ Lower memory usage
- ✅ No local model to load
- ✅ Requires Qdrant Cloud account

```bash
pip install -r requirements-workshop.txt
# or
pip install -r requirements.txt  # Same result - sentence-transformers commented out
```

**Use Local Embeddings** (For offline/development):
- ⚠️ Slower setup (~5-7 minutes)
- ⚠️ Higher memory usage (~500MB)
- ⚠️ Requires downloading model on first run
- ✅ Works without Qdrant Cloud

```bash
# Edit requirements.txt and uncomment sentence-transformers
pip install -r requirements.txt
```

## Both Requirements Files Are Now Identical

Both `requirements.txt` and `requirements-workshop.txt` now have the same setup:
- ✅ sentence-transformers and transformers are **commented out**
- ✅ Ready for cloud inference (default)
- ✅ Same fast installation time

## What Changed

**Before**:
- Requirements included sentence-transformers
- Always loaded embeddings locally
- ~500MB+ memory usage
- 5-7 minute installation

**After**:
- Requirements commented out sentence-transformers  
- Uses Qdrant Cloud Inference by default
- Lower memory usage
- 2-3 minute installation
- Same functionality!

## Switching Between Modes

### Using Cloud Inference (Current Default)
```bash
# In backend/.env
QDRANT_CLOUD_INFERENCE=true  # or just don't set it (defaults to true)
```

Install with either requirements file:
```bash
pip install -r requirements.txt
```

### Using Local Embeddings
```bash
# 1. Uncomment in requirements.txt:
# sentence-transformers==3.2.1
# transformers==4.46.2

# 2. Install dependencies
pip install -r requirements.txt

# 3. Disable cloud inference in .env
QDRANT_CLOUD_INFERENCE=false
```

## Testing What You Have

Check if cloud inference is active:
```bash
curl -X POST http://localhost:8000/query/ \
  -H "Authorization: Bearer admin" \
  -H "Content-Type: application/json" \
  -d '{"query":"test","mode":"local","top_k":1}'
```

Look for `"cloud_inference_used": true` in the response.

## Summary

✅ **Workshop setup**: Both requirements files are ready  
✅ **Cloud inference**: Default and working (tested!)  
✅ **Faster install**: 2-3 minutes vs 5-7 minutes  
✅ **Lower memory**: No local embedding model  
✅ **Same functionality**: Qdrant handles embeddings server-side

