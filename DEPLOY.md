# Deploying CIMS SAGE 2 for 24/7 access (free)

Goal: make the chatbot reachable from anywhere, any time, even when your laptop
is off. Two pieces are needed:

1. A **hosted LLM** so the AI no longer depends on local Ollama.
2. A **cloud host** for the FastAPI app.

---

## Step 1 - Get a free LLM API key (Groq)

1. Go to https://console.groq.com/keys and sign in (free).
2. Create an API key and copy it (starts with `gsk_...`).

The app is already wired for this. When the env var `LLM_API_KEY` is set, it
uses the hosted API automatically (no Ollama needed). Optional overrides:

```
LLM_API_KEY=gsk_xxx                       # required to enable hosted mode
LLM_BASE_URL=https://api.groq.com/openai/v1   # default (Groq)
LLM_MODEL=llama-3.1-8b-instant                # default
```

You can test this locally too:

```bash
export LLM_API_KEY=gsk_xxx
python3 -m uvicorn backend.app:app --port 8000
# open http://127.0.0.1:8000/health/llm  -> should show provider: hosted
```

---

## Step 2 - Deploy the app (Hugging Face Spaces, free, enough RAM)

The app downloads a small local embedding model, so pick a host with a few GB
of RAM. Hugging Face Spaces (free) works well.

1. Create an account at https://huggingface.co
2. New -> Space -> **SDK: Docker** -> blank.
3. Push this repository's files into the Space (or connect the GitHub repo).
4. In Space **Settings -> Variables and secrets**, add a secret:
   - `LLM_API_KEY` = your Groq key
5. The included `Dockerfile` builds and starts automatically. The app reads the
   `PORT` provided by the platform.
6. On first boot the knowledge base auto-seeds from
   `backend/storage/data/knowledge_base.txt`.

When the Space is running you get a public URL like
`https://<user>-<space>.hf.space` - share that on WhatsApp. It stays up without
your laptop.

> Render / Railway also work: connect the repo, set `LLM_API_KEY`, and they
> inject `PORT` automatically. Make sure the instance has enough RAM for the
> embedding model.

---

## Notes

- To add data after deployment, use `/docs` -> `/admin/upload/pdf` or
  `/admin/upload/url` on the live URL.
- `/health/llm` tells you which provider is active and whether it is OK.
