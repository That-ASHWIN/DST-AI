"""
Cache APIs
"""
import logging
import sys
import threading

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(
    prefix="/admin/cache",
    tags=["Cache"],
)

logger = logging.getLogger(__name__)

# Simple in-memory cache placeholder.
# Later Redis se replace kar sakte ho.
# NOTE: nothing currently reads/writes this cache elsewhere in the codebase —
# /stats and /clear will report 0 items until caching logic is wired up.
CACHE = {}
CACHE_LOCK = threading.Lock()
CACHE_TYPE = "In-Memory"


@router.get("/stats")
def cache_stats():
    with CACHE_LOCK:
        item_count = len(CACHE)
        approx_bytes = sys.getsizeof(CACHE) + sum(
            sys.getsizeof(k) + sys.getsizeof(v) for k, v in CACHE.items()
        )

    return {
        "cache_items": item_count,
        "cache_type": CACHE_TYPE,
        "approx_size_kb": round(approx_bytes / 1024, 2),
    }


@router.post("/clear")
def clear_cache(
    confirm: bool = Query(
        False,
        description="Must be explicitly set to true to actually clear the cache. "
                     "Safety guard against accidental clearing.",
    ),
):
    """
    Clears the in-memory cache.

    Requires `?confirm=true` to run. Calling without it returns 400 and
    leaves the cache untouched.
    """
    if not confirm:
        logger.warning("Cache clear called without confirmation — aborting, no items removed.")
        raise HTTPException(
            status_code=400,
            detail="This will clear the cache. Pass ?confirm=true to proceed.",
        )

    with CACHE_LOCK:
        removed = len(CACHE)
        CACHE.clear()

    logger.info("Cache cleared (%s item(s) removed).", removed)

    return {
        "success": True,
        "removed_items": removed,
        "message": "Cache cleared successfully.",
    }