FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set PYTHONPATH to include src/ for src layout
ENV PYTHONPATH=/app/src

# Launcher (python -m manifest) requires opencode on PATH; it is not installed in this image.
# For view-only, override: docker run ... python -m manifest.view.app --manifest-dir /app/.manifest
CMD ["python", "-m", "manifest"]
