"""ChromaDB storage layer with department-aware metadata filtering."""
import logging, uuid
from typing import Any, Dict, List, Optional
import chromadb
from backend.config import VECTOR_DB_DIR, TOP_K_RESULTS
logger=logging.getLogger(__name__); COLLECTION_NAME="cims_knowledge_base"
client=chromadb.PersistentClient(path=str(VECTOR_DB_DIR)); collection=client.get_or_create_collection(name=COLLECTION_NAME)
def normalize_department(department: Optional[str]) -> str:
    if not department: return "general"
    return department.strip().lower().replace(" ","-").replace("_","-") or "general"
def add_documents(chunks:List[str], embeddings:List[List[float]], metadatas:Optional[List[Dict[str,Any]]]=None, department:Optional[str]=None)->List[str]:
    if not chunks or not embeddings: return []
    if len(chunks)!=len(embeddings): raise ValueError("chunks and embeddings length must match")
    dept=normalize_department(department)
    if metadatas is None: metadatas=[{} for _ in chunks]
    if len(metadatas)!=len(chunks): raise ValueError("metadatas length must match chunks")
    clean=[]
    for m in metadatas:
        item={k:v for k,v in (m or {}).items() if v is not None}
        item["department"]=normalize_department(str(item.get("department") or dept))
        clean.append(item)
    ids=[str(uuid.uuid4()) for _ in chunks]
    collection.add(ids=ids,documents=chunks,embeddings=embeddings,metadatas=clean)
    logger.info("Added %s chunks to %s for department=%s",len(chunks),COLLECTION_NAME,dept)
    return ids
def search(query_embedding:List[float], top_k:int=TOP_K_RESULTS, department:Optional[str]=None)->Dict[str,Any]:
    if not query_embedding: raise ValueError("query_embedding cannot be empty")
    count=collection.count()
    if count==0: return {"documents":[[]],"distances":[[]],"metadatas":[[]],"ids":[[]]}
    kwargs={"query_embeddings":[query_embedding],"n_results":min(top_k,count)}
    dept=normalize_department(department) if department and department!="auto" else None
    if dept and dept!="general": kwargs["where"]={"department":dept}
    results=collection.query(**kwargs)
    if dept and dept!="general" and not (results.get("documents") or [[]])[0]:
        results=collection.query(query_embeddings=[query_embedding],n_results=min(top_k,count),where={"department":"general"})
    return results
def clear_database()->None:
    global collection
    try: client.delete_collection(COLLECTION_NAME)
    except Exception as e: logger.warning("Could not delete collection: %s",e)
    collection=client.get_or_create_collection(name=COLLECTION_NAME)
def get_document_count()->int: return collection.count()
