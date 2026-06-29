"""Department-aware RAG pipeline."""
import logging

from backend.core.llm import generate_response, stream_response
from backend.core.prompts import SYSTEM_PROMPT
from backend.core.retrieval import retrieve_context_as_text, detect_department
from backend.utils.lang_detect import detect_language

logger = logging.getLogger(__name__)

NO_CONTEXT_FALLBACK = {
    "english": "Sorry, I couldn't find this information in the selected department knowledge base. Please check the official department page or contact the centre directly.",
    "hindi": "क्षमा करें, यह जानकारी चयनित विभाग के नॉलेज बेस में उपलब्ध नहीं है। कृपया आधिकारिक विभाग पेज देखें या केंद्र से संपर्क करें।",
    "hinglish": "Sorry, ye information selected department knowledge base me available nahi hai. Please official department page check karein ya centre se contact karein.",
}

LLM_ERROR_FALLBACK = {
    "english": "Sorry, I'm having trouble generating a response right now. Please try again in a moment.",
    "hindi": "क्षमा करें, अभी उत्तर तैयार करने में समस्या आ रही है। कृपया थोड़ी देर बाद पुनः प्रयास करें।",
    "hinglish": "Sorry, abhi response generate karne me problem aa rahi hai. Please thodi der baad try karein.",
}

LANGUAGE_INSTRUCTIONS = {
    "english": "Respond only in English.",
    "hindi": "केवल हिंदी में जवाब दें।",
    "hinglish": "Respond in natural Hinglish using Roman script.",
}


def build_prompt(query: str, context: str, department: str, lang: str) -> str:
    return f"""{SYSTEM_PROMPT}

{LANGUAGE_INSTRUCTIONS[lang]}
You are CIMS Sage, a professional department-level university AI assistant.
Selected/Detected department: {department}.
Answer only from the provided context. If context is insufficient, say so clearly.
Use clean Markdown with bullets/tables where useful.

USER QUESTION:
{query}

KNOWLEDGE BASE CONTEXT:
{context}
"""


def generate_rag_response(query: str, department: str | None = None) -> str:
    if not query or not query.strip():
        return "Please enter a valid question."

    lang = detect_language(query)
    dept = detect_department(query, department)
    context = retrieve_context_as_text(query, department=dept)

    if not context:
        return NO_CONTEXT_FALLBACK[lang]

    try:
        return generate_response(build_prompt(query, context, dept, lang)).strip()
    except Exception as e:
        logger.error("LLM failed: %s", e)
        return f"{LLM_ERROR_FALLBACK[lang]} (Reason: {e})"


def stream_rag_response(query: str, department: str | None = None):
    if not query or not query.strip():
        yield "Please enter a valid question."
        return

    lang = detect_language(query)
    dept = detect_department(query, department)
    context = retrieve_context_as_text(query, department=dept)

    if not context:
        yield NO_CONTEXT_FALLBACK[lang]
        return

    try:
        any_token = False
        for token in stream_response(build_prompt(query, context, dept, lang)):
            any_token = True
            yield token
        if not any_token:
            yield LLM_ERROR_FALLBACK[lang]
    except Exception as e:
        logger.error("Streaming LLM failed: %s", e)
        yield f"{LLM_ERROR_FALLBACK[lang]} (Reason: {e})"
