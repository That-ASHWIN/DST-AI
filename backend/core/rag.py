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

# Out-of-scope refusal. Must match the exact sentence in prompts.py (Rule A).
# When the bot produces this, we return ONLY this clean message - no related
# links and no contact footer.
OUT_OF_SCOPE_MESSAGE = (
    "I'm sorry, but I can't help with that. As DST AI, I'm an academic "
    "assistant and can only answer questions related to the studies and topics "
    "of DST-CIMS, BHU."
)
_SCOPE_SIGNATURE = "only answer questions related to the studies and topics"


def is_refusal(text: str) -> bool:
    return _SCOPE_SIGNATURE in (text or "").lower()


# ---------------------------------------------------------------------------
# Official DST-CIMS / BHU links (only verified, real URLs are used here so the
# demo never shows a broken link).
# ---------------------------------------------------------------------------
HOME_URL = "https://www.bhu.ac.in/site/UnitHomeTemplate/1_233_3536_DST-Centre-for-Interdisciplinary-Mathematical-Sciences-Home"
FACULTY_URL = "https://www.bhu.ac.in/site/FacultyList/1_233_3538_DST-Centre-for-Interdisciplinary-Mathematical-Sciences-Faculty"
ADMISSION_URL = "https://admission.bhu.ac.in"
RESEARCH_URL = "https://bhu.irins.org/faculty/index/DST+Centre+for+Interdisciplinary+Mathematical+Sciences"

# topic key -> (label, url, [trigger keywords]). Order = display order.
RELATED_LINKS = {
    "faculty": ("DST-CIMS Faculty page", FACULTY_URL,
                ["faculty", "professor", "teacher", "teachers", "staff",
                 "coordinator", "director", "head", "teaching", "mentor"]),
    "courses": ("DST-CIMS Programmes & courses", HOME_URL,
                ["course", "courses", "programme", "program", "m.sc", "msc",
                 "syllabus", "subject", "subjects", "study", "degree", "phd",
                 "ph.d"]),
    "admission": ("BHU Admission portal", ADMISSION_URL,
                  ["admission", "admissions", "eligibility", "apply", "entrance",
                   "cuet", "intake", "application", "qualify", "seat", "seats"]),
    "research": ("DST-CIMS Research & publications", RESEARCH_URL,
                 ["research", "publication", "publications", "paper", "papers",
                  "areas", "area", "journal", "project", "projects"]),
    "fees": ("BHU fees & scholarships", ADMISSION_URL,
             ["fee", "fees", "scholarship", "scholarships", "fellowship",
              "stipend", "cost", "funding"]),
    "contact": ("DST-CIMS contact / department home", HOME_URL,
                ["contact", "email", "phone", "address", "reach", "location",
                 "where"]),
}

# Mandatory Contact Footer (two trailing spaces = Markdown hard line break).
CONTACT_FOOTER = (
    "\n\nFor further information, please contact:  \n"
    "Coordinator: Prof. Bankteshwar Tiwari  \n"
    "Email: dstcims@gmail.com  \n"
    "Phone: 0542-2369337"
)


def build_related_links(query: str) -> str:
    """Return a Markdown 'Related links' block based on what the user asked."""
    q = (query or "").lower()
    out = []
    seen = set()
    for _key, (label, url, keywords) in RELATED_LINKS.items():
        if any(k in q for k in keywords) and url not in seen:
            seen.add(url)
            out.append((label, url))
    if not out:
        out = [("DST-CIMS official website", HOME_URL)]
    lines = "\n".join(f"- [{label}]({url})" for label, url in out)
    return f"\n\n\U0001F517 **Related links:**\n{lines}"


def build_trailer(query: str) -> str:
    """Related links + mandatory contact footer, appended to in-scope answers."""
    return build_related_links(query) + CONTACT_FOOTER


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
        if is_refusal(answer):
            return OUT_OF_SCOPE_MESSAGE
        return answer + build_trailer(query)
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
        full = ""
        for token in stream_response(build_prompt(query, context, dept, lang)):
            any_token = True
            full += token
            yield token
        if not any_token:
            yield LLM_ERROR_FALLBACK[lang]
            return
        if is_refusal(full):
            return
        yield build_trailer(query)
    except Exception as e:
        logger.error("Streaming LLM failed: %s", e)
        yield f"{LLM_ERROR_FALLBACK[lang]} (Reason: {e})"
