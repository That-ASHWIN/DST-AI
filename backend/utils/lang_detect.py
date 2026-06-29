"""
lang_detect.py
Detects whether a query is English, Hindi, or Hinglish (Hindi written
in Roman script). Pure code-based detection — does NOT rely on the LLM,
since small local models (like llama3.2:3b) don't reliably follow
language instructions in the system prompt.
"""

import re

HINGLISH_MARKERS = {
    "hai", "hain", "kya", "kaise", "kyun", "kyu", "kab", "kahan", "kaun",
    "mujhe", "mujhko", "tumhe", "aap", "tum", "hum", "mein", "mei", "me",
    "ka", "ki", "ke", "ko", "se", "par", "pe", "bhi", "nahi", "nahin",
    "karo", "karna", "kro", "krna", "diya", "dena", "bata", "batao",
    "chahiye", "wala", "wali", "tarah", "matlab", "yaar", "bhai",
}

DEVANAGARI_PATTERN = re.compile(r"[\u0900-\u097F]")


def detect_language(query: str) -> str:
    """
    Returns one of: "hindi", "hinglish", "english".
    """
    if not query or not query.strip():
        return "english"

    if DEVANAGARI_PATTERN.search(query):
        return "hindi"

    words = re.findall(r"[a-zA-Z]+", query.lower())
    if not words:
        return "english"

    hinglish_hits = sum(1 for w in words if w in HINGLISH_MARKERS)
    ratio = hinglish_hits / len(words)

    if hinglish_hits >= 1 and ratio >= 0.15:
        return "hinglish"

    return "english"