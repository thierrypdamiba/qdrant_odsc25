#!/bin/bash

echo "Loading Simple Wikipedia Dataset"
echo "================================"
echo ""

cd backend

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install datasets library if needed
echo "Ensuring dependencies are installed..."
pip install -q datasets tqdm

# Run the script
echo ""
echo "Starting dataset download and processing..."
echo "This will take 5-10 minutes depending on your internet speed."
echo ""

# Default to 1000 articles, but allow override
NUM_ARTICLES=${1:-1000}

python scripts/load_simple_wikipedia.py --num-articles $NUM_ARTICLES

echo ""
echo "Done! You can now start the backend and query the data."


