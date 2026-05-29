#!/bin/bash
# News Portal — start script
set -e

cd "$(dirname "$0")"

echo "=== News Portal ==="

# Check for .env
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copy .env.example to .env and fill in values."
    cp .env.example .env
    echo "   Created .env from .env.example — edit it before running."
    exit 1
fi

# Check for Groq API key
if grep -q 'GROQ_API_KEY=$' .env; then
    echo "⚠️  GROQ_API_KEY is not set in .env."
    echo "   Get a free key at https://console.groq.com"
fi

# Install deps if needed
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate

if ! python -c "import fastapi" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r backend/requirements.txt
fi

# Build frontend if present
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    echo "Building frontend..."
    (cd frontend && npm install && npm run build)
fi

# Start backend
echo "Starting server on http://0.0.0.0:8000"
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
