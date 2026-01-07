FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy all application code
COPY . .

# Expose port
EXPOSE $PORT

# Working startup command
ENTRYPOINT []
CMD ["sh", "-c", "cd backend && exec python -m uvicorn olifan_backend_api:app --host 0.0.0.0 --port $PORT"]