# 🚀 CIMS SAGE

> AI-powered Knowledge Assistant for **DST – Centre for Interdisciplinary Mathematical Sciences (DST-CIMS), Banaras Hindu University**

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED)
![ChromaDB](https://img.shields.io/badge/VectorDB-ChromaDB-orange)
![LangChain](https://img.shields.io/badge/RAG-LangChain-red)
![Ollama](https://img.shields.io/badge/LLM-Ollama-black)
![License](https://img.shields.io/badge/License-MIT-blue)

---

## 📖 Overview

CIMS SAGE is a production-ready Retrieval-Augmented Generation (RAG) platform built for the [DST Centre for Interdisciplinary Mathematical Sciences (DST-CIMS), Banaras Hindu University](https://www.bhu.ac.in/site/UnitHomeTemplate/1_233_3536_DST-Centre-for-Interdisciplinary-Mathematical-Sciences-Home).

The system enables semantic search, intelligent document retrieval, and natural language interaction with institutional knowledge. CIMS SAGE combines **FastAPI**, **ChromaDB**, **Sentence Transformers**, and an **Ollama LLM** to deliver accurate, context-aware responses — using retrieval-based grounding to minimize hallucinations and keep answers anchored to the actual knowledge base.

Instead of manually searching through PDFs and institutional documents, users ask questions in natural language and get answers generated directly from indexed, verifiable source material.

---

## ✨ Features

**AI Features**

- Retrieval-Augmented Generation (RAG)
- Semantic Search
- Context-aware Question Answering
- Hallucination Mitigation via Retrieval Grounding

**Knowledge Base**

- PDF Upload & Ingestion
- URL Content Ingestion
- Automatic Chunking
- Vector Embeddings (ChromaDB)
- Knowledge Base Re-indexing

**Backend**

- FastAPI REST API
- Swagger / ReDoc API Documentation
- Health & Readiness Monitoring
- Admin APIs (Stats, Cache, Logs)
- Docker Support

**Security**

- Request ID Middleware
- Input Validation (Pydantic)
- Global Exception Handling
- Confirmation Guards on Destructive Operations
- CORS Support

---

## 🏗 Architecture

```txt
User
   │
   ▼
FastAPI API Layer
   │
   ▼
Chat Controller
   │
   ▼
RAG Pipeline
   │
   ├────────► Embedding Model
   │
   ├────────► ChromaDB
   │
   ▼
Ollama LLM
   │
   ▼
Final Response
```

---

## 🛠 Tech Stack

**Backend**

- FastAPI
- Python 3.11
- Pydantic

**AI**

- LangChain
- Ollama
- Sentence Transformers

**Database**

- ChromaDB

**Document Processing**

- PyPDF
- python-docx

**Deployment**

- Docker
- Docker Compose

---

## ⚡ Performance

- **Vector Database:** ChromaDB
- **Embedding Model:** all-MiniLM-L6-v2
- **Vector Similarity:** Cosine Similarity
- **Top-K Retrieval:** Configurable
- **LLM:** Ollama (Llama 3.1)
- **Average Retrieval:** < 1 second (hardware dependent)

---

## 📂 Project Structure

```txt
backend/
 ├── app.py
 ├── config.py
 │
 ├── core/
 ├── routes/
 ├── storage/
 ├── ingestion/
 ├── utils/
 ├── logs/

frontend/
 ├── static/
 ├── templates/

docs/

Dockerfile
docker-compose.yml
requirements.txt
README.md
```

---

## ⚙ Installation

Clone the repository:

```bash
git clone https://github.com/That-ASHWIN/DST-AI.git
cd DST-AI
```

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

> On Windows PowerShell, use:
>
> ```powershell
> .venv\Scripts\Activate.ps1
> ```

Install dependencies:

```bash
pip install -r requirements.txt
```

Install and start Ollama, then pull the required model:

```bash
ollama pull llama3.1:8b
ollama serve
```

Run the server:

```bash
python3 -m uvicorn backend.app:app --reload
```

---

## 🔧 Environment Variables

Create a `.env` file in the project root. You can copy the example file:

```bash
cp .env.example .env
```

Then configure the following values:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHUNK_SIZE=500
CHUNK_OVERLAP=100
TOP_K_RESULTS=5
MAX_UPLOAD_SIZE=26214400
```

> Keep `.env` private. Do not commit local environment files or credentials to GitHub.

---

## 🌐 API Documentation

**Swagger UI**

```txt
http://localhost:8000/docs
```

**ReDoc**

```txt
http://localhost:8000/redoc
```

---

## 📌 Important API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/chat` | Ask the AI assistant |
| POST | `/upload/pdf` | Upload a PDF document |
| POST | `/upload/url` | Ingest content from a URL |
| GET | `/` | API root / status |
| GET | `/health` | Lightweight overall health status |
| GET | `/health/live` | Liveness probe |
| GET | `/health/ready` | Readiness probe (checks DB) |
| GET | `/health/system` | System info (Python, platform, uptime) |
| GET | `/admin/stats` | Vector database stats |
| DELETE | `/admin/clear` | Clear vector database *(requires `?confirm=true`)* |
| GET | `/admin/health` | Admin DB health check |
| POST | `/admin/reindex` | Rebuild knowledge base *(requires `?confirm=true`)* |
| GET | `/admin/info` | Knowledge base info (PDFs, chunks, size) |
| GET | `/admin/files` | List uploaded PDF files |
| GET | `/admin/cache/stats` | Cache statistics |
| POST | `/admin/cache/clear` | Clear cache *(requires `?confirm=true`)* |
| GET | `/admin/logs/` | List log files |
| GET | `/admin/logs/latest` | Get the most recent log file |
| DELETE | `/admin/logs/clear` | Delete all log files *(requires `?confirm=true`)* |

> ⚠️ All destructive admin operations (clear, reindex, cache clear, log clear) require an explicit `?confirm=true` query parameter as a safety guard against accidental data loss.

---

## 🔐 Security

- Request ID Middleware
- Global Exception Handling
- Input Validation (Pydantic)
- CORS Support
- Confirmation Guards on Destructive Admin Routes
- Health & Readiness Monitoring
- Production Logging

---

## 📊 Current Status

| Component | Status |
|-----------|--------|
| Backend | ✅ Production Ready |
| REST APIs | ✅ Complete |
| Knowledge Base | ✅ Complete |
| Docker | ✅ Configured |
| Swagger | ✅ Complete |
| Documentation | ✅ Complete |

---

## 🚀 Future Improvements

- User Authentication & RBAC
- Redis Distributed Cache
- PostgreSQL Metadata Store
- Streaming Responses
- Cloud Deployment
- Admin Analytics Dashboard
- Conversation History
- Multi-document Collections

---

## 👨‍💻 Developed By

**Ashwin Dubey**  
Electronics & Communication Engineering  
Chandigarh University

---

## 📄 License

This project is released under the **MIT License**.
