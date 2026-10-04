"""
AI Security Research OS - Backend
Main FastAPI Application Entry Point
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config.settings import settings
from database.db import init_db, get_db
from routes import scan, config as config_routes, reports, capabilities

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting AI Security Research OS Backend")
    await init_db()
    logger.info("✅ Database initialized")
    yield
    # Shutdown
    logger.info("🛑 Shutting down backend")

# Initialize FastAPI app
app = FastAPI(
    title="AI Security Research OS",
    description="AI-powered automated security research platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health Check Endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "AI Security Research OS",
        "version": "1.0.0"
    }

# Root Endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "AI Security Research OS API",
        "docs": "/docs",
        "status": "running",
        "status code": 200
    }

# Include Routers
app.include_router(scan.router, prefix="/api/scan", tags=["Scanning"])
app.include_router(config_routes.router, prefix="/api/config", tags=["Configuration"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(capabilities.router, prefix="/api/capabilities", tags=["Capabilities"])

# Error Handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
