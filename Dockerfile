
# =========================
# Base image
# =========================
FROM python:3.11-slim

# =========================
# Environment variables
# =========================
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# =========================
# Working directory
# =========================
WORKDIR /app

# =========================
# System dependencies
# =========================
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# =========================
# Install Python dependencies
# =========================
COPY requirements.txt .

RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# =========================
# Copy application
# =========================
COPY . .

# =========================
# Application port
# =========================
EXPOSE 7000

# =========================
# Start FastAPI
# =========================
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7000"]
