# CIMS SAGE Testing Guide

## Objective
This checklist verifies that all core backend modules are functioning correctly before deployment or project demonstration.

---

# Environment

- Python Virtual Environment Activated
- Ollama Running
- FastAPI Running
- ChromaDB Initialized

---

# API Tests

## Root

**GET** `/`

Expected:
- Status 200

---

## Health

**GET** `/health`

Expected:
- Status 200
- Response: `{"status": "healthy", "service": "CIMS SAGE"}`

---

**GET** `/health/live`

Expected:
- Status 200
- Response: `{"alive": true}`

---

**GET** `/health/ready`

Expected:
- Status 200
- Response: `{"ready": true}`

---

## PDF Upload

**POST** `/upload/pdf`

Upload one PDF

Expected:
- Status 200
- `success = true`
- Chunks indexed

---

## URL Upload

**POST** `/upload/url`

Expected:
- Status 200
- URL indexed successfully

---

## Chat

**POST** `/chat`

Ask: "What is DST-CIMS?"

Expected:
- Status 200
- AI response generated
- `request_id` present

---

## Admin

**GET** `/admin/stats`

Expected:
- Status 200
- Chunk count returned

---

**GET** `/admin/info`

Expected:
- Status 200
- PDF count returned

---

**GET** `/admin/files`

Expected:
- Status 200
- Uploaded PDFs listed

---

**GET** `/admin/cache/stats`

Expected:
- Status 200
- Cache statistics returned

---

**GET** `/admin/logs`

Expected:
- Status 200
- Log files listed

---

# Swagger

Open [http://localhost:8000/docs](http://localhost:8000/docs)

Expected:
- All endpoints visible
- Interactive API explorer working

---

# Performance

Average response time: **< 3 seconds**

---

# Final Checklist

- ✅ FastAPI Running
- ✅ Ollama Running
- ✅ ChromaDB Connected
- ✅ Upload Working
- ✅ Chat Working
- ✅ Admin APIs Working
- ✅ Health APIs Working
- ✅ Swagger Working
- ✅ Documentation Complete
- ✅ Ready for Demo
