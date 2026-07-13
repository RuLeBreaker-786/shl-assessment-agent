#!/usr/bin/env bash
set -euo pipefail

# Simple dev helper to start backend (uvicorn) and frontend (streamlit).
# It does not install packages automatically; run `pip install -r requirements.txt` first.

if ! command -v uvicorn >/dev/null 2>&1; then
  echo "uvicorn not found. Install dependencies with:"
  echo "  pip install -r requirements.txt"
  exit 1
fi

# Start backend in background
echo "Starting backend: uvicorn main:app --reload"
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Give backend a second to start
sleep 1

# Start streamlit in foreground
echo "Starting frontend: streamlit run streamlit_app.py"
streamlit run streamlit_app.py || true

# When streamlit exits, kill background backend
kill $BACKEND_PID || true

