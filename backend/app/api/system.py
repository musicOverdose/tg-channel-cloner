import os
import shutil
import tempfile
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from backend.app.config import settings
from backend.app.models import User, utcnow
from backend.app.schemas import SystemInfoResponse
from backend.app.workers.job_manager import job_manager
from backend.app.api.deps import get_current_user

router = APIRouter(tags=["system"])


@router.get("/health")
async def health_check():
    """Health check endpoint for Docker Compose / Portainer."""
    return {"status": "ok", "timestamp": utcnow().isoformat()}


@router.get("/api/system/info", response_model=SystemInfoResponse)
async def system_info(_: User = Depends(get_current_user)):
    db_type = "PostgreSQL" if "postgres" in settings.DATABASE_URL else "SQLite"
    active_workers = len([t for t in job_manager.active_tasks.values() if not t.done()])

    return SystemInfoResponse(
        version="1.0.0",
        status="healthy",
        database_type=db_type,
        max_concurrent_jobs=settings.MAX_CONCURRENT_JOBS,
        active_workers=active_workers,
        system_time_utc=utcnow(),
    )


@router.get("/api/system/backup")
async def download_backup(_: User = Depends(get_current_user)):
    """Download a point-in-time snapshot of the SQLite database file."""
    if "sqlite" not in settings.DATABASE_URL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Automated file backup is only supported for SQLite databases. For PostgreSQL, use pg_dump.",
        )

    # Locate SQLite file path
    path_part = settings.DATABASE_URL.split("sqlite+aiosqlite:///")[-1]
    db_file = Path(path_part)
    if not db_file.exists():
        # Fallback check
        local_db = Path(__file__).resolve().parent.parent.parent / "data" / "cloner.db"
        if local_db.exists():
            db_file = local_db
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Database file not found on disk",
            )

    # Create temporary copy to avoid read locks during active WAL operations
    temp_dir = tempfile.gettempdir()
    timestamp_str = utcnow().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"cloner_backup_{timestamp_str}.db"
    backup_path = Path(temp_dir) / backup_filename

    shutil.copy2(db_file, backup_path)

    return FileResponse(
        path=backup_path,
        filename=backup_filename,
        media_type="application/octet-stream",
    )
