FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y curl gcc build-essential && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud hosts (Render, HF Spaces, Railway) inject a PORT env var.
# Default to 8000 for local runs.
ENV PORT=8000
EXPOSE 8000

HEALTHCHECK CMD curl --fail http://localhost:${PORT:-8000}/health/live || exit 1

CMD ["sh", "-c", "uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
