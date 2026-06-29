# CIMS SAGE API Documentation

## Base URL

```
http://localhost:8000
```

---

# Authentication
Currently, authentication is not required. All APIs are publicly accessible during development.

---

# Chat API

## POST `/chat`
Generates an AI response using the Retrieval-Augmented Generation (RAG) pipeline.

### Request

```json
{
  "query": "What are the research areas of DST-CIMS?"
}
```

### Response

```json
{
  "response": "DST-CIMS focuses on interdisciplinary mathematical sciences...",
  "request_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
}
```

---

# PDF Upload

## POST `/upload/pdf`
Uploads a PDF, extracts text, generates embeddings and stores them in ChromaDB.

Supported format:

- PDF

---

# URL Upload

## POST `/upload/url`
Downloads webpage content and indexes it into the knowledge base.

Example

```json
{
    "url":"https://example.com"
}
```

---

# Health APIs

## GET `/health`
Returns service status.

---

## GET `/health/live`
Liveness probe.

---

## GET `/health/ready`
Checks database readiness.

---

## GET `/health/system`
Returns Python version, operating system and uptime.

---

# Admin APIs

## GET `/admin/stats`
Returns vector database statistics.

---

## DELETE `/admin/clear?confirm=true`
Deletes the complete knowledge base.

---

## POST `/admin/reindex?confirm=true`
Rebuilds the knowledge base from uploaded PDFs.

---

## GET `/admin/info`
Returns knowledge base information.

---

## GET `/admin/files`
Lists uploaded PDF files.

---

# Cache APIs

## GET `/admin/cache/stats`
Returns cache statistics.

---

## POST `/admin/cache/clear?confirm=true`
Clears the application cache.

---

# Logging APIs

## GET `/admin/logs`
Returns available log files.

---

## GET `/admin/logs/latest`
Returns latest application log.

---

## DELETE `/admin/logs/clear?confirm=true`
Deletes log files.

---

# Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 400 | Bad Request |
| 404 | Not Found |
| 422 | Validation Error |
| 500 | Internal Server Error |

---

# Swagger

```
http://localhost:8000/docs
```

---

# ReDoc

```
http://localhost:8000/redoc
```
