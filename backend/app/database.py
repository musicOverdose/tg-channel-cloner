import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import event
from backend.app.config import settings

# Adjust database URL if running locally and /data is not accessible
db_url = settings.DATABASE_URL
if db_url.startswith("sqlite+aiosqlite:////data/"):
    # If /data does not exist and cannot be created (e.g. non-docker dev environment), fallback to ./data
    data_dir = Path("/data")
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError):
        local_data = Path(__file__).resolve().parent.parent.parent / "data"
        local_data.mkdir(parents=True, exist_ok=True)
        db_url = f"sqlite+aiosqlite:///{local_data}/cloner.db"
elif db_url.startswith("sqlite"):
    # Ensure directory of sqlite file exists
    path_part = db_url.split("sqlite+aiosqlite:///")[-1]
    if path_part and "/" in path_part:
        Path(path_part).parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(
    db_url,
    echo=False,
    connect_args={"check_same_thread": False} if "sqlite" in db_url else {},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db():
    """FastAPI dependency for obtaining an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database tables and set WAL mode for SQLite."""
    async with engine.begin() as conn:
        if "sqlite" in db_url:
            await conn.exec_driver_sql("PRAGMA journal_mode=WAL;")
            await conn.exec_driver_sql("PRAGMA synchronous=NORMAL;")
            await conn.exec_driver_sql("PRAGMA foreign_keys=ON;")
        await conn.run_sync(Base.metadata.create_all)
