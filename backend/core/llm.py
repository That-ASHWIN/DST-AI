"""LLM client.

Two modes, chosen automatically:
  * Hosted mode (USE_HOSTED_LLM): calls an OpenAI-compatible chat API such as
    Groq's free API. Use this for 24/7 cloud deployment - no local Ollama and
    no laptop required.
  * Local mode: calls a local Ollama server. Good for offline development.
"""
import json
import logging
import time

import requests

from backend.config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    USE_HOSTED_LLM,
    LLM_API_KEY,
    LLM_BASE_URL,
    LLM_MODEL,
)

logger = logging.getLogger(__name__)

GENERATE_API = f"{OLLAMA_BASE_URL}/api/generate"
TAGS_API = f"{OLLAMA_BASE_URL}/api/tags"
CHAT_COMPLETIONS_API = f"{LLM_BASE_URL}/chat/completions"

MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 1.5

# Context window large enough to hold the system prompt + a few retrieved
# sections so the model always sees full faculty/contact data. num_predict is
# kept modest so laptops stay responsive.
OPTIONS = {
    "temperature": 0.1,
    "top_p": 0.8,
    "top_k": 20,
    "num_predict": 400,
    "num_ctx": 4096,
    "repeat_penalty": 1.05,
}

# Shared generation settings for the hosted API.
HOSTED_TEMPERATURE = 0.1
HOSTED_MAX_TOKENS = 700

_resolved_model = None


# ======================================================================
# Hosted OpenAI-compatible API (Groq, OpenAI, Together, etc.)
# ======================================================================

def _hosted_headers():
    return {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }


def _hosted_generate(prompt: str) -> str:
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": HOSTED_TEMPERATURE,
        "max_tokens": HOSTED_MAX_TOKENS,
        "stream": False,
    }
    try:
        r = requests.post(CHAT_COMPLETIONS_API, headers=_hosted_headers(), json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        ans = (data["choices"][0]["message"]["content"] or "").strip()
        if not ans:
            raise RuntimeError("Hosted LLM returned an empty response")
        return ans
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        raise RuntimeError("Cannot reach the hosted LLM API. Check network / LLM_BASE_URL.")
    except requests.exceptions.HTTPError as e:
        detail = ""
        try:
            detail = e.response.text
        except Exception:
            pass
        raise RuntimeError(f"Hosted LLM HTTP error (model '{LLM_MODEL}'): {detail or e}")


def _hosted_stream(prompt: str):
    payload = {
        "model": LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": HOSTED_TEMPERATURE,
        "max_tokens": HOSTED_MAX_TOKENS,
        "stream": True,
    }
    try:
        with requests.post(CHAT_COMPLETIONS_API, headers=_hosted_headers(), json=payload, timeout=60, stream=True) as r:
            r.raise_for_status()
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data:"):
                    line = line[len("data:"):].strip()
                if line == "[DONE]":
                    break
                try:
                    data = json.loads(line)
                except Exception:
                    continue
                choices = data.get("choices") or [{}]
                delta = choices[0].get("delta", {}).get("content", "")
                if delta:
                    yield delta
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        raise RuntimeError("Cannot reach the hosted LLM API. Check network / LLM_BASE_URL.")
    except requests.exceptions.HTTPError as e:
        detail = ""
        try:
            detail = e.response.text
        except Exception:
            pass
        raise RuntimeError(f"Hosted LLM HTTP error (model '{LLM_MODEL}'): {detail or e}")


# ======================================================================
# Local Ollama
# ======================================================================

def list_models():
    """Return list of model names available in Ollama. Empty list if unreachable."""
    try:
        r = requests.get(TAGS_API, timeout=5)
        r.raise_for_status()
        return [m.get("name", "") for m in r.json().get("models", []) if m.get("name")]
    except Exception as e:
        logger.warning("Could not list Ollama models: %s", e)
        return []


def resolve_model():
    """Pick a usable Ollama model, falling back gracefully if the exact tag is missing."""
    global _resolved_model
    if _resolved_model:
        return _resolved_model

    models = list_models()
    if not models:
        return OLLAMA_MODEL

    if OLLAMA_MODEL in models:
        _resolved_model = OLLAMA_MODEL
    else:
        base = OLLAMA_MODEL.split(":")[0]
        match = next((m for m in models if m.split(":")[0] == base), None)
        _resolved_model = match or models[0]
        logger.warning(
            "Configured model '%s' not found. Using '%s'. Available: %s",
            OLLAMA_MODEL, _resolved_model, models,
        )
    return _resolved_model


def check_ollama():
    """Diagnostic for /health/llm. Reports hosted mode if a hosted key is set."""
    if USE_HOSTED_LLM:
        return {
            "provider": "hosted",
            "base_url": LLM_BASE_URL,
            "model": LLM_MODEL,
            "api_key_set": True,
            "hint": "OK (using hosted LLM API - works 24/7 in the cloud)",
        }

    models = list_models()
    reachable = bool(models)
    configured_present = any(
        m == OLLAMA_MODEL or m.split(":")[0] == OLLAMA_MODEL.split(":")[0]
        for m in models
    )
    return {
        "provider": "ollama",
        "ollama_url": OLLAMA_BASE_URL,
        "reachable": reachable,
        "configured_model": OLLAMA_MODEL,
        "configured_model_present": configured_present,
        "available_models": models,
        "model_in_use": resolve_model() if reachable else None,
        "hint": (
            "OK" if (reachable and configured_present)
            else "Run 'ollama serve' and pull a light model, e.g. 'ollama pull llama3.2:3b'"
        ),
    }


# ======================================================================
# Public API (auto-routes to hosted or local)
# ======================================================================

def generate_response(prompt: str, temperature: float = 0.2, max_retries: int = MAX_RETRIES) -> str:
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty")

    if USE_HOSTED_LLM:
        return _hosted_generate(prompt)

    model = resolve_model()
    payload = {"model": model, "prompt": prompt, "stream": False, "options": OPTIONS}
    last = RuntimeError("Unknown error")

    for attempt in range(1, max_retries + 2):
        try:
            r = requests.post(GENERATE_API, json=payload, timeout=120)
            r.raise_for_status()
            ans = r.json().get("response", "").strip()
            if not ans:
                raise RuntimeError("Ollama returned an empty response")
            return ans
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            last = RuntimeError("Cannot connect to Ollama. Is 'ollama serve' running?")
            if attempt <= max_retries:
                time.sleep(RETRY_DELAY_SECONDS)
        except requests.exceptions.HTTPError as e:
            detail = ""
            try:
                detail = e.response.text
            except Exception:
                pass
            raise RuntimeError(f"Ollama HTTP error (model '{model}'): {detail or e}")
        except Exception as e:
            raise RuntimeError(str(e))
    raise last


def stream_response(prompt: str):
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty")

    if USE_HOSTED_LLM:
        yield from _hosted_stream(prompt)
        return

    model = resolve_model()
    payload = {"model": model, "prompt": prompt, "stream": True, "options": OPTIONS}
    try:
        with requests.post(GENERATE_API, json=payload, timeout=120, stream=True) as r:
            r.raise_for_status()
            for line in r.iter_lines(decode_unicode=True):
                if not line:
                    continue
                data = json.loads(line)
                token = data.get("response", "")
                if token:
                    yield token
                if data.get("done"):
                    break
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        raise RuntimeError("Cannot connect to Ollama. Is 'ollama serve' running?")
    except requests.exceptions.HTTPError as e:
        detail = ""
        try:
            detail = e.response.text
        except Exception:
            pass
        raise RuntimeError(f"Ollama HTTP error (model '{model}'): {detail or e}")
