"""Department-aware semantic retrieval."""
import logging, re, time
from typing import List, Optional
from backend.config import TOP_K_RESULTS
from backend.utils.embeddings import get_embedding
from backend.storage.vector_db import search, normalize_department
logger=logging.getLogger(__name__)
# Distance filtering is disabled by default (None). For a small, curated
# department knowledge base it was over-aggressive and dropped valid sections
# (e.g. the FACULTY list), making the bot say it "couldn't find" data that was
# actually present. We instead rely on TOP_K + the LLM's judgement (Rule A in
# the system prompt still refuses truly out-of-scope questions).
MAX_RELEVANT_DISTANCE=None
DEPT_ALIASES={"computer-science":["computer science","cse","cs","computing","mca","bca"],"mathematics":["math","mathematics","msc maths","statistics"],"mba":["mba","management","business administration"],"general":["admission","fees","scholarship","hostel","campus"]}
def detect_department(query:str, selected:Optional[str]=None)->str:
    if selected and selected!="auto": return normalize_department(selected)
    q=(query or "").lower()
    for dept,words in DEPT_ALIASES.items():
        if any(re.search(r"\b"+re.escape(w)+r"\b",q) for w in words): return dept
    return "general"
def retrieve_context(query:str, top_k:int=TOP_K_RESULTS, max_distance:Optional[float]=MAX_RELEVANT_DISTANCE, department:Optional[str]=None)->List[str]:
    if not query or not query.strip(): return []
    dept=detect_department(query,department); start=time.perf_counter(); emb=get_embedding(query); logger.info("Embedding %.2fs dept=%s",time.perf_counter()-start,dept)
    results=search(emb,top_k=top_k,department=dept); docs=(results.get("documents") or [[]])[0]; dists=(results.get("distances") or [[]])[0]
    if not docs: return []
    if max_distance is None: return docs
    filtered=[doc for doc,dist in zip(docs,dists) if dist<=max_distance]
    # Safety fallback: never return nothing just because the distance filter was
    # too strict - if everything got filtered out, return the raw top docs.
    return filtered if filtered else docs
def retrieve_context_as_text(query:str, top_k:int=TOP_K_RESULTS, max_distance:Optional[float]=MAX_RELEVANT_DISTANCE, department:Optional[str]=None)->str:
    chunks=retrieve_context(query,top_k,max_distance,department)
    return "\n\n".join(chunks) if chunks else ""
