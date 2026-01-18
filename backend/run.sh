#!/bin/bash
echo "🚀 Starting ISRO Agent Backend..."
source isro_env/bin/activate
uvicorn app.main:app --reload --port 8000
