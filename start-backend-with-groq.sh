#!/bin/bash

echo "Starting Backend with REAL Groq LLM"
echo "==================================="

cd /Users/thierrydamiba/agent/backend

# Kill any existing backend
pkill -f "python -m app.main" 2>/dev/null
sleep 1

# Activate venv
source venv/bin/activate

# Export environment variables
export USE_MOCK_VECTOR_STORE=false
export USE_MOCK_LLM=false  
export USE_MOCK_SEARCH=true
export GROQ_API_KEY=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
export QDRANT_URL=http://localhost:6333

echo "✓ Qdrant: REAL (localhost:6333)"
echo "✓ LLM: Groq API"
echo "✓ Search: Mock"
echo ""

# Run the app
python -m app.main

