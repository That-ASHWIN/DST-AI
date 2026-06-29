# CIMS SAGE Architecture

## Overview
CIMS SAGE follows a modular Retrieval-Augmented Generation (RAG) architecture. The system separates document ingestion, vector storage, retrieval, large language model interaction, and API routing into independent modules for maintainability and scalability.

---

# High-Level Architecture

```
                User
                  │
                  ▼
         FastAPI REST API
                  │
      ┌───────────┴───────────┐
      ▼                       ▼
 Upload APIs              Chat API
      │                       │
      ▼                       ▼
Document Processing      RAG Pipeline
      │                       │
      ▼                       ▼
Chunking & Embeddings   Semantic Retrieval
      │                       │
      ▼                       ▼
     ChromaDB  ◄──────────────┘
                  │
                  ▼
            Ollama (LLM)
                  │
                  ▼
          Generated Response
```

---

# Backend Modules

## Routes
Responsible for exposing REST endpoints.

- Chat
- Upload
- URL Ingestion
- Admin
- Health
- Cache
- Logs
- Re-index

---

## Core
Contains the business logic.

- Chat Controller
- RAG Pipeline
- Prompt Templates
- Retrieval Engine
- LLM Integration

---

## Ingestion
Responsible for converting external documents into searchable knowledge.

- PDF Loader
- URL Loader
- Chunking
- Embedding Generation

---

## Storage
Stores semantic embeddings.

Database:

- ChromaDB

Stored Data:

- Document Chunks
- Embedding Vectors
- Metadata

---

## Utilities
Shared helper functions.

- Embeddings
- Language Detection
- Logging Helpers

---

# Request Flow

1. User sends a question.
2. Query embedding is generated.
3. ChromaDB retrieves the most relevant chunks.
4. Retrieved context is combined with the system prompt.
5. Ollama generates the final response.
6. FastAPI returns the response as JSON.

---

# Design Principles

- Modular
- Scalable
- Production Ready
- Retrieval First
- Low Hallucination
- Stateless APIs
- Docker Compatible
- Easy Cloud Deployment
