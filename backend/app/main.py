import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from backend.app.config import settings
from backend.app.database import init_db, AsyncSessionLocal
from backend.app.models import User
from backend.app.security import get_password_hash
from backend.app.scheduler.persistent_scheduler import persistent_scheduler
from backend.app.api.auth import router as auth_router
from backend.app.api.bots import router as bots_router
from backend.app.api.jobs import router as jobs_router
from backend.app.api.executions import router as executions_router
from backend.app.api.dashboard import router as dashboard_router
from backend.app.api.system import router as system_router
from backend.app.api.ws import router as ws_router

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("telegram_cloner")


async def seed_admin_user():
    """Ensure initial admin account is present in the database."""
    async with AsyncSessionLocal() as session:
        stmt = select(User).limit(1)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()

        if not user:
            logger.info(f"Seeding initial admin user '{settings.ADMIN_USERNAME}'...")
            admin = User(
                username=settings.ADMIN_USERNAME.strip(),
                hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
                is_active=True,
            )
            session.add(admin)
            await session.commit()
            logger.info("Admin user created successfully.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database...")
    await init_db()
    await seed_admin_user()

    logger.info("Starting persistent scheduler...")
    await persistent_scheduler.start()

    yield

    # Shutdown
    logger.info("Shutting down persistent scheduler...")
    await persistent_scheduler.stop()


app = FastAPI(
    title="Telegram Channel Cloner",
    description="Production-grade, self-hosted Telegram channel sync & clone engine.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(system_router)
app.include_router(auth_router)
app.include_router(bots_router)
app.include_router(jobs_router)
app.include_router(executions_router)
app.include_router(dashboard_router)
app.include_router(ws_router)

# Locate frontend static files directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = BASE_DIR / "backend" / "app" / "static"
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"

chosen_static = None
if STATIC_DIR.exists() and (STATIC_DIR / "index.html").exists():
    chosen_static = STATIC_DIR
elif FRONTEND_DIST_DIR.exists() and (FRONTEND_DIST_DIR / "index.html").exists():
    chosen_static = FRONTEND_DIST_DIR

if chosen_static:
    app.mount("/assets", StaticFiles(directory=chosen_static / "assets" if (chosen_static / "assets").exists() else chosen_static), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Don't intercept /api routes or /health
        if full_path.startswith("api/") or full_path == "health":
            return HTMLResponse(status_code=404, content="Not found")

        candidate_file = chosen_static / full_path
        if candidate_file.is_file():
            return FileResponse(candidate_file)
        return FileResponse(chosen_static / "index.html")
else:
    @app.get("/", include_in_schema=False)
    async def root():
        return HTMLResponse(
            "<html><head><title>Telegram Channel Cloner</title></head>"
            "<body style='font-family: sans-serif; background: #0f172a; color: #f8fafc; padding: 40px; text-align: center;'>"
            "<h1>Telegram Channel Cloner API</h1>"
            "<p>API is healthy and operational. Web frontend will be mounted when built.</p>"
            "<p><a href='/docs' style='color: #38bdf8;'>Interactive API Documentation (/docs)</a> | <a href='/health' style='color: #38bdf8;'>Health Check (/health)</a></p>"
            "</body></html>"
        )
