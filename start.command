#!/bin/bash
# ----------------------------------------------------------
# CIMS SAGE 2 - one-click launcher for Mac
# Double-click this file to start everything for the demo.
# First time only, run:  chmod +x start.command
# ----------------------------------------------------------

cd "$(dirname "$0")" || exit 1

MODEL="${OLLAMA_MODEL:-llama3.2:3b}"
export OLLAMA_MODEL="$MODEL"

echo "============================================="
echo "   Starting CIMS SAGE 2 ..."
echo "   Model: $MODEL"
echo "============================================="

# 1) Start Ollama if it is not already running
if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "-> Starting Ollama server..."
  ollama serve >/tmp/cims_ollama.log 2>&1 &
  sleep 5
else
  echo "-> Ollama already running."
fi

# 2) Make sure the light model is available (skips download if present)
echo "-> Checking model ($MODEL)..."
ollama pull "$MODEL"

# 3) Install Python dependencies (quiet)
echo "-> Installing Python dependencies..."
pip3 install -r requirements.txt >/dev/null 2>&1

# 4) Seed the knowledge base if it is empty
echo "-> Loading knowledge base..."
python3 -m backend.ingestion.text_loader

# 5) Open the chatbot in the browser after a short delay
( sleep 4 ; open "http://127.0.0.1:8000/?v=v8" ) &

# 6) Start the backend (Ctrl+C to stop)
echo "-> Launching server at http://127.0.0.1:8000"
python3 -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
