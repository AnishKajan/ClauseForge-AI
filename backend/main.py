"""
LexiScan AI Contract Analyzer - FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import logging
import os

from routers import health, auth, documents, analysis, billing, admin, ingestion, rag, comparison, usage, sso, organization
from core.config import settings
from core.database import engine, Base
from core.middleware import setup_middleware
from core.telemetry import telemetry_service
from core.logging_config import setup_logging

# Setup structured logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting LexiScan API server...", extra={
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    })
    
    # Initialize telemetry
    telemetry_service.initialize_telemetry("lexiscan-backend")
    
    # Create custom metrics
    custom_metrics = telemetry_service.create_custom_metrics()
    app.state.metrics = custom_metrics
    
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("LexiScan API server started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down LexiScan API server...")


# Create FastAPI application
app = FastAPI(
    title="LexiScan AI Contract Analyzer",
    description="AI-powered contract analysis and compliance platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Setup middleware
setup_middleware(app)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])
app.include_router(admin.router, prefix="/api/admin", tags=["administration"])
app.include_router(ingestion.router, tags=["ingestion"])
app.include_router(rag.router, prefix="/api/rag", tags=["rag"])
app.include_router(comparison.router, prefix="/api/compare", tags=["comparison"])
app.include_router(usage.router, prefix="/api/usage", tags=["usage"])
app.include_router(sso.router, prefix="/api", tags=["sso"])
app.include_router(organization.router, prefix="/api", tags=["organization"])


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "LexiScan AI Contract Analyzer API",
        "version": "0.1.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if os.getenv("ENVIRONMENT") == "development" else False
    )