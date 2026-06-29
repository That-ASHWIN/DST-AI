"""
chatbot.py
Main chatbot controller.
Acts as the entry point for all user queries.
"""

import logging

from backend.core.rag import generate_rag_response

logger = logging.getLogger(__name__)

GENERIC_ERROR_MESSAGE = (
    "Sorry, something went wrong while processing your question. "
    "Please try again in a moment."
)

# Cap how much of a raw query is logged. Helps avoid dumping long blocks
# of potentially sensitive user-typed text (names, roll numbers, etc.)
# into plaintext log files. Adjust/remove if your deployment has proper
# log access controls and a real need for full-query logging.
LOG_QUERY_PREVIEW_LENGTH = 60


class CimsSage:
    """
    Main chatbot controller.
    """

    def __init__(self):
        logger.info("CIMS SAGE initialized successfully.")

    def chat(self, query: str) -> str:
        """
        Process a user query and return the chatbot response.
        Never raises — any internal failure is caught and converted
        into a safe, user-facing message.
        """
        if not query or not query.strip():
            return "Please enter a valid question."

        query_preview = query.strip()[:LOG_QUERY_PREVIEW_LENGTH]
        logger.info(f"User query received (preview): {query_preview!r}...")

        try:
            response = generate_rag_response(query)
        except Exception:
            logger.exception("Unexpected error while generating RAG response.")
            return GENERIC_ERROR_MESSAGE

        logger.info("Response generated successfully.")
        return response


# --- Lazy singleton ---
# Avoids instantiating CimsSage() at import time. The instance is created
# only the first time get_chatbot() is called, so simply importing this
# module (e.g. for testing) never triggers any side effects.
_chatbot_instance: "CimsSage | None" = None


def get_chatbot() -> CimsSage:
    """
    Returns the shared CimsSage instance, creating it on first use.
    """
    global _chatbot_instance
    if _chatbot_instance is None:
        _chatbot_instance = CimsSage()
    return _chatbot_instance