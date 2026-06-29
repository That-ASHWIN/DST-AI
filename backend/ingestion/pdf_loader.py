"""PDF ingestion with department metadata."""
import logging
from pathlib import Path
from typing import List, Tuple
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from backend.config import UPLOAD_DIR
from backend.ingestion.chunker import chunk_text
from backend.utils.embeddings import get_embeddings
from backend.storage.vector_db import add_documents, normalize_department
logger=logging.getLogger(__name__)
def extract_pages_from_pdf(pdf_path:Path)->List[Tuple[int,str]]:
    if not pdf_path.exists(): raise FileNotFoundError(f"PDF not found: {pdf_path}")
    reader=PdfReader(str(pdf_path))
    if reader.is_encrypted: reader.decrypt("")
    pages=[]
    for i,p in enumerate(reader.pages,start=1):
        try: text=p.extract_text() or ""
        except Exception as e: logger.warning("Page %s failed: %s",i,e); continue
        if text.strip(): pages.append((i,text))
    return pages
def extract_text_from_pdf(pdf_path:Path)->str: return "\n".join(t for _,t in extract_pages_from_pdf(pdf_path))
def ingest_pdf(pdf_path:Path, department:str="general")->int:
    dept=normalize_department(department); pages=extract_pages_from_pdf(pdf_path)
    chunks=[]; page_nums=[]
    for page,text in pages:
        pc=chunk_text(text); chunks.extend(pc); page_nums.extend([page]*len(pc))
    if not chunks: return 0
    embeddings=get_embeddings(chunks,show_progress=True)
    metas=[{"source":pdf_path.name,"page":page_nums[i],"chunk":i+1,"department":dept} for i in range(len(chunks))]
    add_documents(chunks,embeddings,metas,department=dept); return len(chunks)
def ingest_all_pdfs(department:str="general")->int:
    total=0
    for pdf in sorted(p for p in UPLOAD_DIR.glob("*") if p.suffix.lower()==".pdf"):
        try: total+=ingest_pdf(pdf,department)
        except Exception: logger.exception("Failed %s",pdf.name)
    return total
if __name__=="__main__": print(f"Indexed {ingest_all_pdfs()} chunks")
