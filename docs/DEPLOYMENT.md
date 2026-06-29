# CIMS SAGE Deployment Guide

## Overview
This document explains how to deploy the CIMS SAGE backend locally using Python or with Docker.

---

# System Requirements

- Python 3.11+
- Git
- Ollama
- 8 GB RAM (recommended)
- macOS / Linux / Windows

---

# Clone Repository

```bash
git clone <repository-url>
cd CIMS-SAGE
```

---

# Create Virtual Environment

**Linux / macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows**

```bash
python -m venv .venv
.venv\Scripts\activate
```

---

# Install Dependencies

```bash
pip install -r requirements.txt
```

---

# Configure Environment

Create a `.env` file in the project root.

```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
EMBEDDING_MODEL=all-MiniLM-L6-v2
TOP_K_RESULTS=3
CHUNK_SIZE=500
CHUNK_OVERLAP=100
```

---

# Install Ollama

Download and install Ollama from the official website.

After installation:

```bash
ollama pull llama3.1:8b
```

Start the service:

```bash
ollama serve
```

---

# Run the Backend

```bash
python3 -m uvicorn backend.app:app --reload
```

Server:

```
http://localhost:8000
```

Swagger:

```
http://localhost:8000/docs
```

---

# Docker Deployment

Build the image:

```bash
docker build -t cims-sage .
```

Run:

```bash
docker run -p 8000:8000 --env-file .env cims-sage
```

Using Docker Compose:

```bash
docker compose up -d
```

---

# Verify Deployment

Check these endpoints:

- `/` — API root
- `/health` — Health status
- `/health/live` — Liveness probe
- `/docs` — Swagger documentation

Upload a PDF and verify:

1. PDF upload succeeds.
2. Chunks are indexed.
3. Chat API answers using uploaded content.

---

# Production Recommendations

- Configure CORS for your frontend domain.
- Enable HTTPS using a reverse proxy (e.g., Nginx).
- Store secrets in environment variables.
- Use persistent storage for ChromaDB.
- Rotate and monitor logs regularly.
- Back up uploaded documents and vector database.

---

# Troubleshooting

## Ollama not running

```bash
ollama serve
```

---

## Model missing

```bash
ollama pull llama3.1:8b
```

---

## Dependencies missing

```bash
pip install -r requirements.txt
```

---

## Swagger unavailable

Restart the server:

```bash
python3 -m uvicorn backend.app:app --reload
```

---

# Deployment Status Checklist

- ✅ FastAPI running
- ✅ Ollama connected
- ✅ ChromaDB initialized
- ✅ Swagger accessible
- ✅ PDF upload working
- ✅ URL ingestion working
- ✅ Chat responses generated
- ✅ Health endpoints responding
- ✅ Docker configuration available
