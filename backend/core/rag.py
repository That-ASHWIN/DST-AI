"""
rag.py
Main Retrieval-Augmented Generation (RAG) pipeline.
"""

import logging

from backend.core.llm import generate_response
from backend.core.prompts import SYSTEM_PROMPT
from backend.core.retrieval import retrieve_context_as_text
from backend.utils.lang_detect import detect_language

logger = logging.getLogger(__name__)

# Must match the exact fallback message defined in SYSTEM_PROMPT's
# HALLUCINATION_PREVENTION_RULES section — kept as one constant so the two
# never drift out of sync if either file is edited later.
NO_CONTEXT_FALLBACK = {
    "english": (
        "Sorry, I couldn't find this information in the department knowledge base. "
        "Please refer to the official DST-CIMS website or contact the centre directly "
        "for accurate information."
    ),
    "hindi": (
        "क्षमा करें, यह जानकारी विभाग के नॉलेज बेस में उपलब्ध नहीं है। "
        "कृपया आधिकारिक DST-CIMS वेबसाइट देखें या केंद्र से सीधे संपर्क करें।"
    ),
    "hinglish": (
        "Sorry, ye information department knowledge base me available nahi hai. "
        "Please official DST-CIMS website check karein ya centre se directly contact karein."
    ),
}

LLM_ERROR_FALLBACK = {
    "english": "Sorry, I'm having trouble generating a response right now. Please try again in a moment.",
    "hindi": "क्षमा करें, अभी उत्तर तैयार करने में समस्या आ रही है। कृपया थोड़ी देर बाद पुनः प्रयास करें।",
    "hinglish": "Sorry, abhi response generate karne me problem aa rahi hai. Please thodi der baad try karein.",
}

LANGUAGE_INSTRUCTIONS = {
    "english": "IMPORTANT: Respond ONLY in English. Do not use Hindi or Hinglish.",
    "hindi": "महत्वपूर्ण: केवल हिंदी (देवनागरी लिपि) में जवाब दें। अंग्रेज़ी या Hinglish का उपयोग न करें।",
    "hinglish": (
        "IMPORTANT: Respond ONLY in natural Hinglish (Hindi words written in "
        "Roman/English script). Do NOT use Devanagari script, and do NOT "
        "respond in pure English."
    ),
}


def generate_rag_response(query: str) -> str:
    """
    Main RAG pipeline.

    Flow:
        User Query
            ↓
        Detect Language
            ↓
        Retrieve Context
            ↓
        Build Prompt (only if context found)
            ↓
        LLM
            ↓
        Final Response
    """
    if not query or not query.strip():
        return "Please enter a valid question."

    lang = detect_language(query)
    lang_instruction = LANGUAGE_INSTRUCTIONS[lang]

    context = retrieve_context_as_text(query)

    # If no relevant context was retrieved, short-circuit and return the
    # exact fallback message in the detected language — do NOT call the
    # LLM. This guarantees consistent wording and prevents the model from
    # hallucinating an answer from its own training knowledge when context
    # is missing.
    if not context:
        logger.info(f"No relevant context found for query: {query!r} (lang={lang})")
        return NO_CONTEXT_FALLBACK[lang]

    logger.info(f"Context found for query: {query!r} ({len(context)} chars, lang={lang}).")

    prompt = f"""{SYSTEM_PROMPT}

{lang_instruction}

=========================
USER QUESTION
=========================
{query}

=========================
KNOWLEDGE BASE CONTEXT
=========================
{context}
"""

    try:
        answer = generate_response(prompt)
    except Exception as e:
        logger.error(f"LLM generation failed for query {query!r}: {e}")
        return LLM_ERROR_FALLBACK[lang]

    if not answer or not answer.strip():
        logger.warning(f"LLM returned an empty response for query: {query!r}")
        return LLM_ERROR_FALLBACK[lang]

    return answer.strip()