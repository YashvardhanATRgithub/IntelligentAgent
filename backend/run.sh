#!/bin/bash
echo "🚀 Starting Backend (FastAPI)..."
source isro_env/bin/activate
uvicorn app.main:app --reload --port 8000
