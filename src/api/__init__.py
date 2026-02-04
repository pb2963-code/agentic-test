"""REST API for the health monitoring platform."""

from .app import create_app
from .routes import patients, vitals, medications, symptoms, alerts, wellness, dashboard

__all__ = [
    "create_app",
    "patients",
    "vitals",
    "medications",
    "symptoms",
    "alerts",
    "wellness",
    "dashboard",
]
