"""Vital signs routes."""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ...agents.vital_signs_agent import VitalType
from ...models.database import Database
from ...models.vital_reading import VitalReadingCreate, VitalReadingRepository
from ..dependencies import get_db, get_health_system, HealthMonitoringSystem

router = APIRouter()


class VitalReadingRequest(BaseModel):
    """Request to record a vital reading."""

    patient_id: str
    vital_type: str = Field(..., description="Type of vital sign (heart_rate, blood_pressure_systolic, etc.)")
    value: float
    unit: str
    device_id: str | None = None
    notes: str | None = None


@router.post("/", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def record_vital(
    data: VitalReadingRequest,
    db: Database = Depends(get_db),
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """
    Record a vital sign reading.

    The reading is analyzed by the Vital Signs Agent for anomalies and trends.
    """
    # Save to database
    repo = VitalReadingRepository(db)
    reading = await repo.create(VitalReadingCreate(**data.model_dump()))

    # Process through agent
    if health_system.vital_signs_agent:
        try:
            vital_type = VitalType(data.vital_type)
            analysis = await health_system.vital_signs_agent.record_vital(
                patient_id=data.patient_id,
                vital_type=vital_type,
                value=data.value,
                unit=data.unit,
                device_id=data.device_id,
                notes=data.notes or "",
            )
        except ValueError:
            analysis = {"status": "recorded", "message": "Unknown vital type, stored without analysis"}
    else:
        analysis = {"status": "recorded"}

    return {
        "reading_id": reading.reading_id,
        "analysis": analysis,
        "message": "Vital reading recorded successfully",
    }


@router.get("/{patient_id}", response_model=dict[str, Any])
async def get_patient_vitals(
    patient_id: str,
    vital_type: str | None = None,
    hours: int = 24,
    limit: int = 100,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    """Get vital readings for a patient."""
    repo = VitalReadingRepository(db)
    since = datetime.utcnow() - timedelta(hours=hours)

    readings = await repo.get_by_patient(
        patient_id=patient_id,
        vital_type=vital_type,
        limit=limit,
        since=since,
    )

    return {
        "patient_id": patient_id,
        "readings": [r.model_dump() for r in readings],
        "count": len(readings),
        "period_hours": hours,
    }


@router.get("/{patient_id}/latest", response_model=dict[str, Any])
async def get_latest_vitals(
    patient_id: str,
    db: Database = Depends(get_db),
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Get the latest vital readings for a patient."""
    repo = VitalReadingRepository(db)

    vital_types = [
        "heart_rate",
        "blood_pressure_systolic",
        "blood_pressure_diastolic",
        "temperature",
        "oxygen_saturation",
        "respiratory_rate",
    ]

    latest = {}
    for vt in vital_types:
        reading = await repo.get_latest(patient_id, vt)
        if reading:
            latest[vt] = {
                "value": reading.value,
                "unit": reading.unit,
                "recorded_at": reading.recorded_at.isoformat(),
            }

    return {
        "patient_id": patient_id,
        "latest_vitals": latest,
    }


@router.get("/{patient_id}/statistics", response_model=dict[str, Any])
async def get_vital_statistics(
    patient_id: str,
    vital_type: str,
    days: int = 7,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    """Get statistics for a vital type."""
    repo = VitalReadingRepository(db)
    since = datetime.utcnow() - timedelta(days=days)

    stats = await repo.get_statistics(patient_id, vital_type, since)

    return {
        "patient_id": patient_id,
        "vital_type": vital_type,
        "period_days": days,
        "statistics": stats,
    }


@router.get("/{patient_id}/trends", response_model=dict[str, Any])
async def get_vital_trends(
    patient_id: str,
    hours: int = 24,
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Get trend analysis for all vitals."""
    if not health_system.vital_signs_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vital signs agent not available"
        )

    trends = {}
    for vt in VitalType:
        trend = health_system.vital_signs_agent._calculate_trend(
            patient_id, vt, hours
        )
        if trend.get("direction") != "insufficient_data":
            trends[vt.value] = trend

    return {
        "patient_id": patient_id,
        "window_hours": hours,
        "trends": trends,
    }
