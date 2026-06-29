"""Department-aware RAG pipeline."""
import logging

from backend.core.llm import generate_response, stream_response
from backend.core.prompts import SYSTEM_PROMPT
from backend.core.retrieval import retrieve_context_as_text, detect_department
from backend.utils.lang_detect import detect_language

logger = logging.getLogger(__name__)

LLM_ERROR_FALLBACK = {
    "english": "Sorry, I'm having trouble generating a response right now. Please try again in a moment.",
    "hindi": "\u0915\u094d\u0937\u092e\u093e \u0915\u0930\u0947\u0902, \u0905\u092d\u0940 \u0909\u0924\u094d\u0924\u0930 \u0924\u0948\u092f\u093e\u0930 \u0915\u0930\u0928\u0947 \u092e\u0947\u0902 \u0938\u092e\u0938\u094d\u092f\u093e \u0906 \u0930\u0939\u0940 \u0939\u0948\u0964 \u0915\u0943\u092a\u092f\u093e \u0925\u094b\u0921\u093c\u0940 \u0926\u0947\u0930 \u092c\u093e\u0926 \u092a\u0941\u0928\u0903 \u092a\u094d\u0930\u092f\u093e\u0938 \u0915\u0930\u0947\u0902\u0964",
    "hinglish": "Sorry, abhi response generate karne me problem aa rahi hai. Please thodi der baad try karein.",
}

LANGUAGE_INSTRUCTIONS = {
    "english": "Respond only in English.",
    "hindi": "\u0915\u0947\u0935\u0932 \u0939\u093f\u0902\u0926\u0940 \u092e\u0947\u0902 \u091c\u0935\u093e\u092c \u0926\u0947\u0902\u0964",
    "hinglish": "Respond in natural Hinglish using Roman script.",
}

# Appended to the end of EVERY generated answer (Mandatory Contact Footer).
# Two trailing spaces before each newline = Markdown hard line break, so the
# footer renders on separate lines inside the chat widget.
CONTACT_FOOTER = (
    "\n\nFor further information, please contact:  \n"
    "Coordinator: Prof. Bankteshwar Tiwari  \n"
    "Email: dstcims@gmail.com  \n"
    "Phone: 0542-2369337"
)


def build_prompt(query: str, context: str, department: str, lang: str) -> str:
    ctx = context.strip() if context and context.strip() else "(No specific knowledge base entry was retrieved for this query.)"
    return f"""{SYSTEM_PROMPT}

{LANGUAGE_INSTRUCTIONS[lang]}
Selected/Detected department: {department}.

KNOWLEDGE BASE CONTEXT (highest-priority source of truth - includes admin-uploaded PDFs and URLs):
{ctx}

USER QUESTION:
{query}
"""


def generate_rag_response(query: str, department: str | None = None) -> str:
    if not query or not query.strip():
        return "Please enter a valid question."

    lang = detect_language(query)
    dept = detect_department(query, department)
    context = retrieve_context_as_text(query, department=dept)

    try:
        answer = generate_response(build_prompt(query, context, dept, lang)).strip()
        return answer + CONTACT_FOOTER
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

    try:
        any_token = False
        for token in stream_response(build_prompt(query, context, dept, lang)):
            any_token = True
            yield token
        if not any_token:
            yield LLM_ERROR_FALLBACK[lang]
            return
        yield CONTACT_FOOTER
    except Exception as e:
        logger.error("Streaming LLM failed: %s", e)
        yield f"{LLM_ERROR_FALLBACK[lang]} (Reason: {e})"
