from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from app.auth_router import router as auth_router
from app.users_router import router as users_router
from app.bank_api_router import router as bank_api_router
from app.analytics_router import router as analytics_router
from app.predictions_router import router as predictions_router
from app.ar_router import router as ar_router
from app.counterparty_router import router as counterparty_router
from app.sync_router import router as sync_router
from app.database import engine
from app.models import Base
from app.config import get_settings
import logging

settings = get_settings()
import uvicorn

logger = logging.getLogger(__name__)



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"⚠️  Warning: Database initialization error: {e}")
        # Continue anyway - tables might already exist
    yield
    # Shutdown
    await engine.dispose()

app = FastAPI(
    title="Multi-Banking MVP API",
    description="MVP for multi-banking application for Solo Entrepreneurs with financial analytics, ML predictions, and AR management",
    version="1.0.0",
    lifespan=lifespan
)

# Better validation error handling
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with better error messages"""
    errors = []
    for error in exc.errors():
        field = " -> ".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(f"Validation error on {request.url.path}: {errors}")
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": errors
        }
    )

# CORS - allow frontend origins
# Default local/cDocker origins

CODESPACE_SLUG = "potential-halibut-6x6jgqgvgpxh5q6x"
CODESPACE_BASE = f"https://{CODESPACE_SLUG}.github.dev"

allowed_origins = [
    "http://localhost:5173",      # Vite dev server (local)
    "http://127.0.0.1:5173",      # Vite dev server (local)
    "http://localhost:3000",
    "http://localhost:8000",      # Frontend production (local)
    "http://127.0.0.1:3000",      # Frontend production (local)
    "http://frontend:5173",       # Frontend container (dev)
    "http://frontend:80",         # Frontend container (prod)
    CODESPACE_BASE,
    f"https://{CODESPACE_SLUG}-5173.app.github.dev",
    f"https://{CODESPACE_SLUG}-3000.app.github.dev",
    f"https://{CODESPACE_SLUG}-8000.app.github.dev",
]

# Remove duplicates while preserving order
seen = set()
allowed_origins = [x for x in allowed_origins if not (x in seen or seen.add(x))]

logger.info(f"CORS allowed origins: {allowed_origins}")

# Configure CORS with more permissive settings for development
# Note: When allow_credentials=True, allow_origins cannot contain "*" - must be explicit list
# Using allow_origin_regex to dynamically match all GitHub Codespaces
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Explicit list of allowed origins
    allow_origin_regex=r"https://.*\.github\.dev.*",  # Allow all GitHub Codespaces dynamically
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(bank_api_router)
app.include_router(analytics_router)
app.include_router(predictions_router)
app.include_router(ar_router)
app.include_router(counterparty_router)
app.include_router(sync_router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

# Explicit OPTIONS handler as fallback for all routes
@app.api_route("/{full_path:path}", methods=["OPTIONS"])
async def options_handler(request: Request, full_path: str):
    """Handle OPTIONS preflight requests explicitly"""
    origin = request.headers.get("Origin", "")
    
    headers = {
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD",
        "Access-Control-Allow-Headers": request.headers.get("Access-Control-Request-Headers", "*"),
        "Access-Control-Max-Age": "3600",
    }
    
    # Allow origin if it's in our list or matches GitHub Codespace pattern
    if origin:
        if origin in allowed_origins or "github.dev" in origin:
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Credentials"] = "true"
        else:
            # For any other origin, still allow it (flexible for development)
            headers["Access-Control-Allow-Origin"] = origin
    else:
        headers["Access-Control-Allow-Origin"] = "*"
    
    logger.info(f"OPTIONS preflight: {full_path} from origin: {origin}")
    return JSONResponse(status_code=200, content={}, headers=headers)

