#!/bin/bash

API_URL="http://localhost:8000"

echo "Testing Agentic RAG API"
echo "======================="
echo ""

# Test health endpoint
echo "1. Testing health endpoint..."
curl -s "$API_URL/health" | python3 -m json.tool
echo ""
echo ""

# Test login
echo "2. Testing login (admin user)..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"test"}')
echo "$LOGIN_RESPONSE" | python3 -m json.tool
TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)
echo ""
echo ""

# Test current user
echo "3. Testing /auth/me endpoint..."
curl -s "$API_URL/auth/me" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
echo ""
echo ""

# Test query with local mode
echo "4. Testing query (local mode)..."
curl -s -X POST "$API_URL/query/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning?",
    "mode": "local",
    "top_k": 3
  }' | python3 -m json.tool
echo ""
echo ""

# Test query with internet mode
echo "5. Testing query (internet mode)..."
curl -s -X POST "$API_URL/query/" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the latest developments in AI?",
    "mode": "internet",
    "top_k": 3
  }' | python3 -m json.tool
echo ""
echo ""

# Test local_user (restricted permissions)
echo "6. Testing local_user (should fail on internet search)..."
LOCAL_TOKEN=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"local_user","password":"test"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null)

curl -s -X POST "$API_URL/query/" \
  -H "Authorization: Bearer $LOCAL_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Test query",
    "mode": "internet",
    "top_k": 3
  }' | python3 -m json.tool
echo ""
echo ""

echo "======================="
echo "API Tests Complete!"


