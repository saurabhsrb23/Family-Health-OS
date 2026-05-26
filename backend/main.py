import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings.upload_dir_path.mkdir(parents=True, exist_ok=True)
    init_db()
    logger.info("Praan Health API started")
    yield
    # Shutdown
    logger.info("Praan Health API shutting down")


app = FastAPI(
    title="Family Health OS API",
    version="1.0.0",
    description="Family Health OS — 90-day family care platform",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global exception handlers ─────────────────────────────────────────────────
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "NOT_FOUND", "detail": "Resource not found", "status_code": 404},
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": "INTERNAL_ERROR", "detail": "Internal server error", "status_code": 500},
    )


# ── Core routes ───────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "version": "1.0.0", "environment": settings.ENVIRONMENT}


# ── API router placeholder (routes added in later modules) ────────────────────
from fastapi import APIRouter

api_router = APIRouter(prefix="/api/v1")
# Routers will be included here as each module is built:
# api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
# api_router.include_router(members_router, prefix="/members", tags=["Members"])
# api_router.include_router(programs_router, prefix="/programs", tags=["Programs"])

app.include_router(api_router)
