"""Alert management routes."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ...agents.alert_agent import AlertCategory, AlertSeverity
from ...models.database import Database
from ...models.alert import AlertCreate, AlertRepository
from ..dependencies import get_db, get_health_system, HealthMonitoringSystem

router = APIRouter()


class CreateAlertRequest(BaseModel):
    """Request to create an alert."""

    patient_id: str
    category: str
    severity: int = Field(..., ge=1, le=5)
    title: str
    message: str
    source_agent: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class TriggerEmergencyRequest(BaseModel):
    """Request to trigger emergency."""

    patient_id: str
    reason: str
    location: str | None = None


class ConfigureNotificationsRequest(BaseModel):
    """Request to configure notifications."""

    patient_id: str
    channels: list[dict[str, Any]]


@router.post("/", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_alert(
    data: CreateAlertRequest,
    db: Database = Depends(get_db),
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Create a health alert."""
    # Save to database
    repo = AlertRepository(db)
    alert = await repo.create(AlertCreate(**data.model_dump()))

    # Process through agent
    if health_system.alert_agent:
        try:
            await health_system.alert_agent.create_alert(
                patient_id=data.patient_id,
                category=AlertCategory(data.category),
                severity=AlertSeverity(data.severity),
                title=data.title,
                message=data.message,
                source_agent=data.source_agent or "",
                data=data.data,
            )
        except Exception:
            pass

    return {
        "alert_id": alert.alert_id,
        "message": "Alert created successfully",
    }


@router.get("/{patient_id}", response_model=dict[str, Any])
async def get_patient_alerts(
    patient_id: str,
    active_only: bool = True,
    min_severity: int | None = None,
    db: Database = Depends(get_db),
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Get alerts for a patient."""
    repo = AlertRepository(db)

    if active_only:
        alerts = await repo.get_active_by_patient(patient_id, min_severity)
    else:
        alerts = await repo.get_history(patient_id)

    return {
        "patient_id": patient_id,
        "alerts": [a.model_dump() for a in alerts],
        "count": len(alerts),
    }


@router.post("/{alert_id}/acknowledge", response_model=dict[str, Any])
async def acknowledge_alert(
    alert_id: str,
    db: Database = Depends(get_db),
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Acknowledge an alert."""
    repo = AlertRepository(db)
    await repo.acknowledge(alert_id)

    return {
        "message": "Alert acknowledged",
        "alert_id": alert_id,
    }


@router.post("/{alert_id}/resolve", response_model=dict[str, Any])
async def resolve_alert(
    alert_id: str,
    resolution_notes: str = "",
    db: Database = Depends(get_db),
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Resolve an alert."""
    repo = AlertRepository(db)
    await repo.resolve(alert_id)

    return {
        "message": "Alert resolved",
        "alert_id": alert_id,
    }


@router.post("/emergency", response_model=dict[str, Any])
async def trigger_emergency(
    data: TriggerEmergencyRequest,
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Trigger emergency response."""
    if not health_system.alert_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Alert agent not available"
        )

    alert = await health_system.alert_agent.trigger_emergency(
        patient_id=data.patient_id,
        reason=data.reason,
        location=data.location,
    )

    return {
        "alert_id": alert.alert_id,
        "message": "Emergency response initiated",
        "severity": "EMERGENCY",
    }


@router.post("/notifications/configure", response_model=dict[str, Any])
async def configure_notifications(
    data: ConfigureNotificationsRequest,
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Configure notification channels for a patient."""
    if not health_system.alert_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Alert agent not available"
        )

    health_system.alert_agent.configure_notifications(
        data.patient_id, data.channels
    )

    return {
        "message": "Notifications configured",
        "channels_count": len(data.channels),
    }


@router.get("/{patient_id}/history", response_model=dict[str, Any])
async def get_alert_history(
    patient_id: str,
    limit: int = 50,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    """Get alert history for a patient."""
    repo = AlertRepository(db)
    alerts = await repo.get_history(patient_id, limit)

    return {
        "patient_id": patient_id,
        "history": [a.model_dump() for a in alerts],
        "count": len(alerts),
    }
