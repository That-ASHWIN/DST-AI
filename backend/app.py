"""
app.py
Main FastAPI application for DST AI
"""

import hashlib
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.config import DATA_DIR, VECTOR_DB_DIR
from backend.core.chatbot import get_chatbot
from backend.storage.vector_db import get_document_count
from backend.ingestion.text_loader import load_knowledge_base

from backend.routes.chat_routes import router as chat_router
from backend.routes.health_routes import router as health_router
from backend.routes.upload_routes import router as upload_router
from backend.routes.url_routes import router as url_router
from backend.routes.admin_routes import router as admin_router
from backend.routes.reindex_routes import router as reindex_router
from backend.routes.admin_panel_routes import router as admin_panel_router

# --------------------------------------------------------
# Logging
# --------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)

# --------------------------------------------------------
# Knowledge base auto-seed / auto-refresh helpers
# --------------------------------------------------------

KB_FILE = DATA_DIR / "knowledge_base.txt"
KB_MARKER = VECTOR_DB_DIR / ".kb_version"


def _kb_hash() -> str:
    """MD5 of knowledge_base.txt so we can detect when its content changed."""
    try:
        return hashlib.md5(KB_FILE.read_bytes()).hexdigest()
    except Exception:
        return ""


def _stored_kb_hash() -> str:
    try:
        if KB_MARKER.exists():
            return KB_MARKER.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return ""


def _save_kb_hash(value: str) -> None:
    try:
        KB_MARKER.write_text(value, encoding="utf-8")
    except Exception:
        logger.exception("Could not write KB version marker (non-fatal).")


def _reingest_uploaded_pdfs() -> None:
    """After a KB text reseed (which clears the DB), add back any PDFs that staff
    previously uploaded so their content is not lost."""
    try:
        from backend.ingestion.pdf_loader import ingest_all_pdfs
        added = ingest_all_pdfs()
        if added:
            logger.info("Re-ingested %s chunk(s) from previously uploaded PDFs.", added)
    except Exception:
        logger.exception("Re-ingesting uploaded PDFs failed (continuing without it).")

# --------------------------------------------------------
# Lifespan
# --------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading chatbot...")
    app.state.chatbot = get_chatbot()
    logger.info("Chatbot loaded.")

    # Auto-seed / auto-refresh the knowledge base.
    #   * Fresh deployment (empty DB) -> seed it.
    #   * knowledge_base.txt changed since last run -> re-seed automatically so
    #     the bot always reflects the latest content WITHOUT any manual step.
    # Uploaded PDFs are re-ingested after a text reseed so they aren't wiped.
    try:
        current_hash = _kb_hash()
        stored_hash = _stored_kb_hash()
        count = get_document_count()

        if count == 0:
            reason = "empty knowledge base"
            need_seed = True
        elif current_hash and current_hash != stored_hash:
            reason = "knowledge_base.txt changed since last run"
            need_seed = True
        else:
            need_seed = False

        if need_seed:
            logger.info("Seeding knowledge base (%s) ...", reason)
            inserted = load_knowledge_base()
            logger.info("Seeded knowledge base with %s chunk(s).", inserted)
            _reingest_uploaded_pdfs()
            _save_kb_hash(current_hash)
        else:
            logger.info("Knowledge base up to date (%s chunks). No reseed needed.", count)
    except Exception:
        logger.exception("Knowledge base auto-seed/refresh failed (continuing without it).")

    yield
    logger.info("Server shutting down.")

# --------------------------------------------------------
# FastAPI
# --------------------------------------------------------

app = FastAPI(
    title="DST AI API",
    description="DST AI - Official AI Assistant for DST-CIMS, BHU",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# --------------------------------------------------------
# Routers
# --------------------------------------------------------

app.include_router(chat_router)
app.include_router(health_router)
app.include_router(upload_router)
app.include_router(url_router)
app.include_router(admin_router)
app.include_router(reindex_router)
app.include_router(admin_panel_router)

# Optional routers

for router_name in (
    "info_routes",
    "log_routes",
    "cache_routes",
):
    try:
        module = __import__(
            f"backend.routes.{router_name}",
            fromlist=["router"],
        )

        app.include_router(module.router)

        logger.info(
            "Loaded optional router: %s",
            router_name,
        )

    except Exception as e:

        logger.warning(
            "Skipped optional router %s (%s)",
            router_name,
            e.__class__.__name__,
        )

# --------------------------------------------------------
# CORS
# --------------------------------------------------------

ALLOWED_ORIGINS = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------------------------------------
# Static Files
# --------------------------------------------------------

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

STATIC_DIR = os.path.join(
    BASE_DIR,
    "frontend",
    "static",
)

TEMPLATE_DIR = os.path.join(
    BASE_DIR,
    "frontend",
    "templates",
)

INDEX_FILE = os.path.join(
    TEMPLATE_DIR,
    "index.html",
)

if os.path.isdir(STATIC_DIR):
    app.mount(
        "/static",
        StaticFiles(directory=STATIC_DIR),
        name="static",
    )
    logger.info("Static folder mounted.")

if os.path.isdir(TEMPLATE_DIR):
    templates = Jinja2Templates(directory=TEMPLATE_DIR)

# --------------------------------------------------------
# Middleware
# --------------------------------------------------------

@app.middleware("http")
async def add_request_id(request: Request, call_next):

    request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    start = time.perf_counter()

    response = await call_next(request)

    elapsed = round(
        (time.perf_counter() - start) * 1000,
        2,
    )

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = str(elapsed)

    logger.info(
        "%s %s %s %.2f ms",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )

    return response

# --------------------------------------------------------
# Exception Handler
# --------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(
    request: Request,
    exc: Exception,
):

    logger.exception(exc)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal Server Error",
            "request_id": getattr(
                request.state,
                "request_id",
                None,
            ),
        },
    )

# --------------------------------------------------------
# Frontend
# --------------------------------------------------------

@app.get("/", include_in_schema=False)
async def home():

    if os.path.isfile(INDEX_FILE):
        return FileResponse(INDEX_FILE)

    return {
        "message": "Frontend not found."
    }

# --------------------------------------------------------
# API Status
# --------------------------------------------------------

@app.get("/api")
async def api_status():

    return {
        "status": "ok",
        "version": app.version,
        "project": "DST AI",
    }
