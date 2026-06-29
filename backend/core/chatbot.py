"""Main chatbot controller."""
import logging
from backend.core.rag import generate_rag_response, stream_rag_response
logger=logging.getLogger(__name__); GENERIC_ERROR_MESSAGE="Sorry, something went wrong while processing your question. Please try again."
class CimsSage:
    def __init__(self): logger.info("CIMS SAGE 2 initialized.")
    def chat(self, query:str, department:str|None=None)->str:
        if not query or not query.strip(): return "Please enter a valid question."
        try: return generate_rag_response(query,department)
        except Exception: logger.exception("RAG error"); return GENERIC_ERROR_MESSAGE
    def stream_chat(self, query:str, department:str|None=None):
        try: yield from stream_rag_response(query,department)
        except Exception: logger.exception("Streaming RAG error"); yield GENERIC_ERROR_MESSAGE
_chatbot_instance=None
def get_chatbot()->CimsSage:
    global _chatbot_instance
    if _chatbot_instance is None: _chatbot_instance=CimsSage()
    return _chatbot_instance
