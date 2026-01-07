#!/bin/bash
set -e

# Debug: Check what Python executables are available
echo "Checking available Python executables:"
which python3 || echo "python3 not found"
which python || echo "python not found"
ls -la /usr/bin/python* 2>/dev/null || echo "No Python in /usr/bin"
ls -la /opt/python*/bin/python* 2>/dev/null || echo "No Python in /opt"

# Try different Python paths
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
elif [ -f "/opt/python/bin/python3" ]; then
    PYTHON_CMD="/opt/python/bin/python3"
elif [ -f "/usr/local/bin/python3" ]; then
    PYTHON_CMD="/usr/local/bin/python3"
else
    echo "No Python found!"
    exit 1
fi

echo "Using Python: $PYTHON_CMD"

# Navigate to backend directory
cd backend

# Install Python dependencies
echo "Installing Python dependencies..."
$PYTHON_CMD -m pip install -r requirements.txt

# Start the application
echo "Starting Olifan backend..."
exec $PYTHON_CMD -m uvicorn olifan_backend_api:app --host 0.0.0.0 --port $PORT