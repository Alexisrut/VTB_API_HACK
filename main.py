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
allowed_origins = [
    "http://localhost:5173",      # Vite dev server (local)
    "http://127.0.0.1:5173",      # Vite dev server (local)
    "http://localhost:3000",      # Frontend production (local)
    "http://127.0.0.1:3000",      # Frontend production (local)
    "http://frontend:5173",       # Frontend container (dev)
    "http://frontend:80",         # Frontend container (prod)
]

# Add custom origins from environment if specified
if hasattr(settings, 'CORS_ORIGINS') and settings.CORS_ORIGINS:
    custom_origins = settings.CORS_ORIGINS.split(',')
    allowed_origins.extend([origin.strip() for origin in custom_origins])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
