"""URL ingestion with department metadata and SSRF guard."""
import ipaddress, logging, socket
from typing import List, Optional, Tuple
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from backend.ingestion.chunker import chunk_text
from backend.utils.embeddings import get_embeddings
from backend.storage.vector_db import add_documents, normalize_department
logger=logging.getLogger(__name__); ALLOWED_SCHEMES={"http","https"}; MAX_CONTENT_BYTES=15*1024*1024; HEADERS={"User-Agent":"CIMS-SAGE-2/1.0"}
def _private(host):
    try: infos=socket.getaddrinfo(host,None)
    except socket.gaierror: return True
    for info in infos:
        ip=ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast: return True
    return False
def _validate(url):
    p=urlparse(url)
    if p.scheme not in ALLOWED_SCHEMES or not p.hostname or _private(p.hostname): raise ValueError("Invalid/private URL is not allowed")
def extract_text_from_url(url:str)->Tuple[str,Optional[str]]:
    _validate(url)
    with requests.get(url,headers=HEADERS,timeout=(10,20),stream=True) as r:
        r.raise_for_status(); raw=b""
        for c in r.iter_content(8192):
            raw+=c
            if len(raw)>MAX_CONTENT_BYTES: raise ValueError("Page too large")
        html=raw.decode(r.encoding or r.apparent_encoding or "utf-8",errors="replace")
    soup=BeautifulSoup(html,"html.parser"); title=soup.title.get_text(strip=True) if soup.title else None
    for tag in soup(["script","style","noscript","header","footer","nav"]): tag.decompose()
    lines=[x.strip() for x in soup.get_text("\n").splitlines() if x.strip()]
    return "\n".join(lines),title
def ingest_url(url:str, department:str="general")->int:
    dept=normalize_department(department); text,title=extract_text_from_url(url.rstrip("/"))
    chunks=chunk_text(text)
    if not chunks: return 0
    embeddings=get_embeddings(chunks,show_progress=True)
    metas=[{"source":url,"title":title or url,"chunk":i+1,"department":dept} for i in range(len(chunks))]
    add_documents(chunks,embeddings,metas,department=dept); return len(chunks)
def ingest_multiple_urls(urls:List[str],department:str="general")->int: return sum(ingest_url(u,department) for u in urls)
