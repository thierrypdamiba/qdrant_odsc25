#!/bin/bash

echo "Starting Agentic RAG Frontend..."
echo "================================"

cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Run the dev server
echo "Starting Next.js on http://localhost:3000"
echo "================================"
npm run dev


