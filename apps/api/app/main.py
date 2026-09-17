"""
FastAPI application entry point.

Provides REST API for the WoW Combat Log AI Analyzer.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import reports
from app.services.wcl_client import WCLClient

logger = logging.getLogger(__name__)

# Global WCL client instance (shared across requests)
wcl_client: WCLClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — startup and shutdown."""
    global wcl_client
    wcl_client = WCLClient()
    logger.info("WCL client initialized")
    yield
    if wcl_client:
        await wcl_client.close()
        logger.info("WCL client closed")


app = FastAPI(
    title="WoW Combat Log AI Analyzer",
    description=(
        "Analyze Warcraft Logs reports with deterministic rule-based analysis "
        "and AI-powered coaching."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(reports.router)


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.1.0"}
