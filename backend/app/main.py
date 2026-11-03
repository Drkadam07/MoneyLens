import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import (
    MoneyLensException,
    generic_exception_handler,
    moneylens_exception_handler,
)
from app.core.logging import logger, setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} in {settings.APP_ENV} mode...")
    yield
    logger.info(f"Shutting down {settings.APP_NAME}...")


app = FastAPI(
    title="MoneyLens API",
    description="AI-Powered Personal Finance Intelligence Platform with Deterministic Financial Ledger",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Request ID middleware
@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
app.add_exception_handler(MoneyLensException, moneylens_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include Router
app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "message": "Welcome to MoneyLens - AI-Powered Personal Finance Intelligence Platform",
        "documentation": "/docs",
        "health": "/api/v1/health",
    }
