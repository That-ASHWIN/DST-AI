"""
app.py
Main FastAPI application for DST AI
"""

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
# Lifespan
# --------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Loading chatbot...")
    app.state.chatbot = get_chatbot()
    logger.info("Chatbot loaded.")

    # Auto-seed the knowledge base on a fresh deployment (e.g. a cloud server
    # with an empty disk) so the bot has data to answer from without any
    # manual step.
    try:
        if get_document_count() == 0:
            logger.info("Knowledge base is empty - auto-seeding from knowledge_base.txt ...")
            inserted = load_knowledge_base()
            logger.info("Auto-seeded knowledge base with %s chunk(s).", inserted)
    except Exception:
        logger.exception("Knowledge base auto-seed failed (continuing without it).")

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
