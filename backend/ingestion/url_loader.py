"""
url_loader.py
Loads web pages, extracts text, chunks it,
creates embeddings, and stores them in ChromaDB.
"""
import ipaddress
import logging
import socket
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from backend.ingestion.chunker import chunk_text
from backend.utils.embeddings import get_embeddings
from backend.storage.vector_db import add_documents

logger = logging.getLogger(__name__)

ALLOWED_SCHEMES = {"http", "https"}
ALLOWED_CONTENT_TYPES = ("text/html", "application/xhtml+xml", "text/plain")
MAX_CONTENT_BYTES = 15 * 1024 * 1024  # 15 MB safety cap

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0 Safari/537.36"
    )
}


def _is_private_host(hostname: str) -> bool:
    """
    Resolve hostname and check if it points to a private/loopback/
    link-local address (basic SSRF guard). Fails closed (treats
    unresolved hosts as private) so we never silently allow them.
    """
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return True
    for info in infos:
        ip_str = info[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return True
    return False


def _validate_url(url: str) -> None:
    """
    Raise ValueError if the URL is malformed, uses a disallowed
    scheme, or resolves to a private/internal address.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"Unsupported URL scheme: {url!r} (only http/https allowed)")
    if not parsed.hostname:
        raise ValueError(f"Could not determine host for URL: {url!r}")
    if _is_private_host(parsed.hostname):
        raise ValueError(f"Refusing to fetch internal/private address: {url!r}")


def extract_text_from_url(url: str) -> Tuple[str, Optional[str]]:
    """
    Download a webpage and extract clean text.

    Returns:
        (text, page_title)
    """
    _validate_url(url)

    with requests.get(
        url,
        headers=HEADERS,
        timeout=(10, 20),  # (connect, read) timeouts
        stream=True,
    ) as response:
        response.raise_for_status()

        content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if content_type and not any(content_type.startswith(ct) for ct in ALLOWED_CONTENT_TYPES):
            raise ValueError(f"Unsupported content type '{content_type}' for {url}")

        # Read with a hard size cap to avoid memory blowups on huge/streamed pages.
        raw = b""
        for chunk in response.iter_content(chunk_size=8192):
            raw += chunk
            if len(raw) > MAX_CONTENT_BYTES:
                raise ValueError(f"Page too large (> {MAX_CONTENT_BYTES} bytes): {url}")

        response.encoding = response.encoding or response.apparent_encoding
        html = raw.decode(response.encoding or "utf-8", errors="replace")

    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("title")
    page_title = title_tag.get_text(strip=True) if title_tag else None

    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()

    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines), page_title


def ingest_url(url: str) -> int:
    """
    Ingest a single webpage into ChromaDB.

    Returns:
        Number of chunks inserted.
    """
    url = url.rstrip("/")
    logger.info("Ingesting URL: %s", url)

    try:
        text, page_title = extract_text_from_url(url)
    except ValueError:
        # Validation/content errors: don't wrap, message is already clear.
        raise
    except Exception as e:
        logger.exception("Failed to fetch URL: %s", url)
        raise RuntimeError(f"Failed to fetch {url}: {e}") from e

    if not text.strip():
        logger.warning("No text extracted from %s", url)
        return 0

    chunks = chunk_text(text)
    if not chunks:
        logger.warning("No chunks generated for %s", url)
        return 0

    embeddings = get_embeddings(chunks, show_progress=True)

    metadatas = [
        {
            "source": url,
            "title": page_title,
            "chunk": i + 1,
        }
        for i in range(len(chunks))
    ]
    add_documents(
        chunks=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    logger.info("Indexed %d chunks from %s", len(chunks), url)
    return len(chunks)


def ingest_multiple_urls(urls: List[str]) -> int:
    """
    Ingest multiple URLs.

    Returns:
        Total chunks indexed.
    """
    total = 0
    failed: List[str] = []
    for url in urls:
        try:
            total += ingest_url(url)
        except Exception:
            logger.exception("Failed to ingest %s", url)
            failed.append(url)

    logger.info("Total URL chunks indexed: %d", total)
    if failed:
        logger.warning("Failed URLs (%d): %s", len(failed), ", ".join(failed))
    return total


if __name__ == "__main__":
    urls = [
        "https://dstcims.in/",
    ]
    total = ingest_multiple_urls(urls)
    print(f"\nIndexed {total} URL chunks.")