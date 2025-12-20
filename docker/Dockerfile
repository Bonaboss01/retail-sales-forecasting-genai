FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for xgboost)
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (better caching)
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy project source
COPY src ./src
COPY models ./models

# Expose API port
EXPOSE 8000

# Run FastAPI app
CMD ["python", "-m", "uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
