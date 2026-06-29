"""Shared route dependencies."""
import logging

from fastapi import Header, HTTPException

from backend.config import ADMIN_KEY

logger = logging.getLogger(__name__)


def require_admin(x_admin_key: str | None = Header(default=None)):
    """Gate admin/ingestion endpoints behind ADMIN_KEY.

    If ADMIN_KEY is not configured (empty), access is open - handy for local
    development. On a public deployment, set ADMIN_KEY so only staff who know
    the key can upload PDFs/URLs.
    """
    if not ADMIN_KEY:
        return
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing admin key.")
