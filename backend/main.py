"""News Portal — FastAPI application."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from database import init_db
from config import get_settings
from api.categories import router as categories_router
from api.sources import router as sources_router

# Optional routers — gracefully skip if not yet implemented
try:
    from api.news import router as news_router
except ImportError:
    news_router = None
try:
    from api.users import router as users_router
except ImportError:
    users_router = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    settings = get_settings()
    # Start scheduler (imported here to avoid circular imports)
    try:
        from scheduler import setup_scheduler
        setup_scheduler(settings)
    except ImportError:
        pass
    yield
    # Shutdown
    try:
        from scheduler import shutdown_scheduler
        shutdown_scheduler()
    except ImportError:
        pass


app = FastAPI(
    title=get_settings().app_name,
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(categories_router, prefix="/api")
app.include_router(sources_router, prefix="/api")
if news_router is not None:
    app.include_router(news_router, prefix="/api")
if users_router is not None:
    app.include_router(users_router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok", "name": get_settings().app_name}


# Mount SvelteKit static frontend (production build)
frontend_build = Path(__file__).resolve().parent.parent / "frontend" / "build"
if frontend_build.exists():
    app.mount("/", StaticFiles(directory=str(frontend_build), html=True), name="static")
