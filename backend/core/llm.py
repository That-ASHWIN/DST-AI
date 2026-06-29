"""
llm.py
Handles communication with the local Ollama LLM.
"""

import logging
import time

import requests

from backend.config import (
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
)

logger = logging.getLogger(__name__)

GENERATE_API = f"{OLLAMA_BASE_URL}/api/generate"

MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 1.5


def generate_response(
    prompt: str,
    temperature: float = 0.2,
    max_retries: int = MAX_RETRIES,
) -> str:
    """
    Send prompt to Ollama and return the generated response.

    Retries on transient connection errors (e.g. Ollama momentarily busy),
    up to `max_retries` times, before giving up.
    """
    logger.info(f"Using Ollama model: {OLLAMA_MODEL}")

    if not prompt or not prompt.strip():
        raise ValueError("Prompt cannot be empty.")

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.8,
            "top_k": 20,
            "num_predict": 220,
            "num_ctx": 2048,
            "repeat_penalty": 1.05,
            "num_thread": 8,
        },
    }

    last_error: Exception = RuntimeError("Unknown error.")

    for attempt in range(1, max_retries + 2):  # +2 = first try + retries
        try:
            response = requests.post(
                GENERATE_API,
                json=payload,
                timeout=40,
            )
            response.raise_for_status()
            result = response.json()
            answer = result.get("response", "").strip()

            if not answer:
                logger.error("Ollama returned an empty response.")
                raise RuntimeError("Ollama returned an empty response.")

            logger.info("LLM response generated successfully.")
            return answer

        except requests.exceptions.Timeout:
            logger.error(f"Ollama request timed out (attempt {attempt}/{max_retries + 1}).")
            last_error = RuntimeError("LLM request timed out.")

        except requests.exceptions.ConnectionError:
            logger.error(
                f"Cannot connect to Ollama (attempt {attempt}/{max_retries + 1})."
            )
            last_error = RuntimeError(
                "Cannot connect to Ollama. Is 'ollama serve' running?"
            )

        except RuntimeError:
            # Empty-response case already logged above — don't retry,
            # since the request succeeded but had nothing useful to say.
            raise

        except Exception as e:
            logger.exception("LLM generation failed.")
            raise RuntimeError(str(e))

        # Only reached after Timeout/ConnectionError — wait before retrying.
        if attempt <= max_retries:
            time.sleep(RETRY_DELAY_SECONDS)

    # All retries exhausted.
    raise last_error