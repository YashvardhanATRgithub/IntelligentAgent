#!/bin/bash
echo "🛑 Stopping ISRO Agent Backend..."
pkill -f uvicorn
echo "✅ Backend stopped."
