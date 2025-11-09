from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
import uvicorn



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()

app = FastAPI(
    title="Multi-Banking MVP API",
    description="MVP for multi-banking application for Solo Entrepreneurs with financial analytics, ML predictions, and AR management",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173",
                   "http://localhost:5173"],
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
