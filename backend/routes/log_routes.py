"""
Logging APIs
"""
import logging
from pathlib import Path
from typing import List

from fastapi import APIRouter, HTTPException, Query

from backend.config import LOG_DIR

router = APIRouter(
    prefix="/admin/logs",
    tags=["Logs"],
)

logger = logging.getLogger(__name__)


def _list_log_files() -> List[Path]:
    """Returns all .log files in LOG_DIR. Empty list if LOG_DIR is missing."""
    log_dir = Path(LOG_DIR)
    if not log_dir.exists():
        logger.warning("LOG_DIR does not exist: %s", log_dir)
        return []
    return list(log_dir.glob("*.log"))


def _safe_size_kb(path: Path) -> float:
    """Returns file size in KB, or 0 if the file vanished mid-request."""
    try:
        return round(path.stat().st_size / 1024, 2)
    except FileNotFoundError:
        logger.warning("Log file disappeared while reading size: %s", path.name)
        return 0.0


@router.get("/")
def list_logs():
    files = [
        {"name": log.name, "size_kb": _safe_size_kb(log)}
        for log in _list_log_files()
    ]
    files.sort(key=lambda x: x["name"])
    return {
        "count": len(files),
        "logs": files,
    }


@router.delete("/clear")
def clear_logs(
    confirm: bool = Query(
        False,
        description="Must be explicitly set to true to actually delete log files. "
                     "Safety guard against accidental deletion.",
    ),
):
    """
    Deletes all .log files in LOG_DIR.

    Destructive — requires `?confirm=true` to run. Calling without it
    returns 400 and leaves the logs untouched.

    Note: if a log file is currently open for writing (the active log),
    deletion may fail on some platforms — this is reported in `failed`
    rather than raising an error for the whole request.
    """
    if not confirm:
        logger.warning("Log clear called without confirmation — aborting, no files deleted.")
        raise HTTPException(
            status_code=400,
            detail="This will permanently delete all log files. Pass ?confirm=true to proceed.",
        )

    deleted = 0
    failed = []

    for log in _list_log_files():
        try:
            log.unlink()
            deleted += 1
        except Exception:
            logger.exception("Couldn't delete %s", log.name)
            failed.append(log.name)

    return {
        "success": len(failed) == 0,
        "deleted_logs": deleted,
        "failed_logs": failed,
    }


@router.get("/latest")
def latest_log():
    logs = _list_log_files()
    if not logs:
        raise HTTPException(
            status_code=404,
            detail="No log files found.",
        )

    # Sort safely — a file vanishing mid-sort falls back to "oldest" rather than crashing.
    def _mtime_or_zero(path: Path) -> float:
        try:
            return path.stat().st_mtime
        except FileNotFoundError:
            return 0.0

    logs.sort(key=_mtime_or_zero, reverse=True)
    latest = logs[0]

    return {
        "latest_log": latest.name,
        "size_kb": _safe_size_kb(latest),
        "total_logs": len(logs),
    }