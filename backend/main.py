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
    logger.info("Family Health OS API started")
    yield
    # Shutdown
    logger.info("Family Health OS API shutting down")


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


# ── Routers ───────────────────────────────────────────────────────────────────
from routes.auth import router as auth_router                    # noqa: E402
from routes.members import router as members_router              # noqa: E402
from routes.programs import router as programs_router            # noqa: E402
from routes.meals import router as meals_router                  # noqa: E402
from routes.workouts import router as workouts_router            # noqa: E402
from routes.measurements import router as measurements_router    # noqa: E402

app.include_router(auth_router, prefix="/api/v1")
app.include_router(members_router, prefix="/api/v1")
app.include_router(programs_router, prefix="/api/v1")
app.include_router(meals_router, prefix="/api/v1")
app.include_router(workouts_router, prefix="/api/v1")
app.include_router(measurements_router, prefix="/api/v1")

# Future routers (added per module):
# from routes.adherence import router as adherence_router
# from routes.summaries import router as summaries_router
# app.include_router(adherence_router, prefix="/api/v1")
# app.include_router(summaries_router, prefix="/api/v1")
