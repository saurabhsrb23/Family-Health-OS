import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.upload_dir_path.mkdir(parents=True, exist_ok=True)
    init_db()
    logger.info("Family Health OS API started")
    yield
    logger.info("Family Health OS API shutting down")


app = FastAPI(
    title="Family Health OS API",
    version="1.0.0",
    description="Family Health OS — 90-day family care platform",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware (order matters — outermost added last) ─────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from middleware.audit import AuditMiddleware  # noqa: E402
app.add_middleware(AuditMiddleware)


# ── Exception handlers ────────────────────────────────────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Pydantic / FastAPI input validation failures — return structured field errors."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })
    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "detail": "Input validation failed",
            "errors": errors,
            "status_code": 422,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handles all HTTPExceptions raised by route handlers.
    detail may be a dict (our standard error format) or a plain string.
    """
    if isinstance(exc.detail, dict):
        content = {**exc.detail, "timestamp": datetime.utcnow().isoformat()}
    else:
        content = {
            "error": "HTTP_ERROR",
            "detail": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat(),
        }
    return JSONResponse(status_code=exc.status_code, content=content)


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all for unhandled exceptions — never leak stack traces to clients."""
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "detail": "An unexpected error occurred",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "NOT_FOUND",
            "detail": "Resource not found",
            "status_code": 404,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


# ── Core routes ───────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "version": "1.0.0", "environment": settings.ENVIRONMENT}


# ── API Routers ───────────────────────────────────────────────────────────────

from routes.auth import router as auth_router                    # noqa: E402
from routes.members import router as members_router              # noqa: E402
from routes.programs import router as programs_router            # noqa: E402
from routes.meals import router as meals_router                  # noqa: E402
from routes.workouts import router as workouts_router            # noqa: E402
from routes.measurements import router as measurements_router    # noqa: E402
from routes.adherence import router as adherence_router          # noqa: E402
from routes.summaries import router as summaries_router          # noqa: E402

app.include_router(auth_router, prefix="/api/v1")
app.include_router(members_router, prefix="/api/v1")
app.include_router(programs_router, prefix="/api/v1")
app.include_router(meals_router, prefix="/api/v1")
app.include_router(workouts_router, prefix="/api/v1")
app.include_router(measurements_router, prefix="/api/v1")
app.include_router(adherence_router, prefix="/api/v1")
app.include_router(summaries_router, prefix="/api/v1")
