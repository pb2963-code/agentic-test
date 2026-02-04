"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..models.database import get_database
from .routes import patients, vitals, medications, symptoms, alerts, wellness, dashboard
from .dependencies import get_health_system, shutdown_health_system

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("Starting Health Monitoring Platform...")

    # Initialize database
    db = await get_database()
    logger.info("Database initialized")

    # Initialize health monitoring system
    health_system = await get_health_system()
    logger.info("Health monitoring system started")

    yield

    # Shutdown
    logger.info("Shutting down Health Monitoring Platform...")
    await shutdown_health_system()
    await db.disconnect()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Health Monitoring Platform",
        description="""
        A comprehensive multi-agent health monitoring platform for patients and consumers.

        ## Features

        - **Patient Management**: Register and manage patient profiles
        - **Vital Signs Monitoring**: Track heart rate, blood pressure, temperature, and more
        - **Medication Management**: Manage medications, schedules, and adherence
        - **Symptom Tracking**: Log and analyze symptoms
        - **Wellness Tracking**: Track activities, sleep, nutrition, and mood
        - **Smart Alerts**: Receive intelligent health alerts
        - **AI-Powered Insights**: Get personalized health recommendations

        ## Multi-Agent System

        The platform uses a sophisticated multi-agent system with specialized agents:

        - **Vital Signs Agent**: Monitors and analyzes vital signs
        - **Medication Agent**: Manages medication schedules and interactions
        - **Symptom Analysis Agent**: Analyzes symptoms and detects patterns
        - **Wellness Agent**: Tracks lifestyle and wellness data
        - **Alert Agent**: Manages health alerts and notifications
        - **Coordinator Agent**: Orchestrates all agents and provides unified insights
        """,
        version="1.0.0",
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(patients.router, prefix="/api/patients", tags=["Patients"])
    app.include_router(vitals.router, prefix="/api/vitals", tags=["Vital Signs"])
    app.include_router(medications.router, prefix="/api/medications", tags=["Medications"])
    app.include_router(symptoms.router, prefix="/api/symptoms", tags=["Symptoms"])
    app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
    app.include_router(wellness.router, prefix="/api/wellness", tags=["Wellness"])
    app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])

    @app.get("/", tags=["Root"])
    async def root() -> dict[str, Any]:
        """Root endpoint with API information."""
        return {
            "name": "Health Monitoring Platform",
            "version": "1.0.0",
            "status": "running",
            "docs": "/docs",
            "redoc": "/redoc",
        }

    @app.get("/health", tags=["Health"])
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    return app
