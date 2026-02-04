"""API route modules."""

from . import patients, vitals, medications, symptoms, alerts, wellness, dashboard

__all__ = [
    "patients",
    "vitals",
    "medications",
    "symptoms",
    "alerts",
    "wellness",
    "dashboard",
]
