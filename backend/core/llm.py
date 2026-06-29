"""Ollama LLM client with model auto-resolution, normal + streaming generation."""
import json
import logging
import time

import requests

from backend.config import OLLAMA_BASE_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)

GENERATE_API = f"{OLLAMA_BASE_URL}/api/generate"
TAGS_API = f"{OLLAMA_BASE_URL}/api/tags"

MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 1.5

# Lower context + output keeps memory/CPU usage modest so laptops don't hang.
OPTIONS = {
    "temperature": 0.1,
    "top_p": 0.8,
    "top_k": 20,
    "num_predict": 300,
    "num_ctx": 2048,
    "repeat_penalty": 1.05,
}

_resolved_model = None


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
    """Pick a usable model.

    Prefer the configured OLLAMA_MODEL. If it isn't installed, fall back to a
    model with the same base name, otherwise the first installed model. This
    keeps the app working even when the exact tag is missing.
    """
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
    """Diagnostic: report Ollama reachability, installed models, model in use."""
    models = list_models()
    reachable = bool(models)
    configured_present = any(
        m == OLLAMA_MODEL or m.split(":")[0] == OLLAMA_MODEL.split(":")[0]
        for m in models
    )
    return {
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


def generate_response(prompt: str, temperature: float = 0.2, max_retries: int = MAX_RETRIES) -> str:
    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty")

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
