#!/bin/bash

# Inspektor Development Launcher
# This script starts both the Python LLM server and the Tauri client

set -e

echo "🚀 Starting Inspektor in Development Mode"
echo ""

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "⚠️  Warning: Ollama doesn't appear to be running on localhost:11434"
    echo "   Please start Ollama with: ollama serve"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Start Python server in background
echo "📦 Starting Python LLM Server..."
cd server

if [ ! -d "venv" ]; then
    echo "   Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

if [ ! -f ".env" ]; then
    echo "   Creating .env from .env.example..."
    cp .env.example .env
fi

python main.py &
SERVER_PID=$!
cd ..

# Wait for server to be ready
echo "   Waiting for server to start..."
for i in {1..10}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Python server is ready"
        break
    fi
    sleep 1
done

# Start Tauri client
echo "🖥️  Starting Tauri Client..."
cd client

if [ ! -d "node_modules" ]; then
    echo "   Installing npm dependencies..."
    npm install
fi

npm run tauri dev &
CLIENT_PID=$!

# Cleanup function
cleanup() {
    echo ""
    echo "🛑 Shutting down..."
    kill $SERVER_PID 2>/dev/null || true
    kill $CLIENT_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

echo ""
echo "✨ Inspektor is running!"
echo ""
echo "📊 Python Server: http://localhost:8000"
echo "📊 API Docs: http://localhost:8000/docs"
echo "💻 Tauri Client: Will launch automatically"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for both processes
wait
