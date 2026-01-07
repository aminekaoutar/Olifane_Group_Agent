#!/bin/bash
set -e

# Navigate to backend directory
cd backend

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Start the application
echo "Starting Olifan backend..."
exec python -m uvicorn olifan_backend_api:app --host 0.0.0.0 --port $PORT