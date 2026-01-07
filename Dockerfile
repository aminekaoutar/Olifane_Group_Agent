FROM python:3.11-slim

# Set working directory
WORKDIR /app/backend

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ .

# Expose port
EXPOSE $PORT

# Use proper shell execution - this works reliably on Railway
CMD ["sh", "-c", "exec python -m uvicorn olifan_backend_api:app --host 0.0.0.0 --port $PORT"]