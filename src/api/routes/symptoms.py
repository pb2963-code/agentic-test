"""Symptom tracking routes."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ...agents.symptom_agent import SymptomSeverity
from ...models.database import Database
from ...models.symptom import SymptomCreate, SymptomRepository
from ..dependencies import get_db, get_health_system, HealthMonitoringSystem

router = APIRouter()


class ReportSymptomRequest(BaseModel):
    """Request to report a symptom."""

    patient_id: str
    symptom_name: str
    severity: int = Field(..., ge=1, le=4, description="1=Mild, 2=Moderate, 3=Severe, 4=Critical")
    description: str | None = None
    location: str | None = None
    onset_time: datetime | None = None
    duration_hours: float | None = None
    triggers: list[str] = Field(default_factory=list)
    relieving_factors: list[str] = Field(default_factory=list)
    associated_symptoms: list[str] = Field(default_factory=list)
    notes: str | None = None


@router.post("/", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def report_symptom(
    data: ReportSymptomRequest,
    db: Database = Depends(get_db),
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """
    Report a symptom.

    The symptom is analyzed by the Symptom Analysis Agent for patterns
    and risk assessment.
    """
    # Save to database
    repo = SymptomRepository(db)
    symptom = await repo.create(SymptomCreate(
        patient_id=data.patient_id,
        name=data.symptom_name,
        severity=data.severity,
        description=data.description,
        location=data.location,
        onset_time=data.onset_time,
        duration_hours=data.duration_hours,
        triggers=data.triggers,
    ))

    # Process through agent
    analysis = {}
    if health_system.symptom_agent:
        try:
            result = await health_system.symptom_agent.report_symptom(
                patient_id=data.patient_id,
                symptom_name=data.symptom_name,
                severity=SymptomSeverity(data.severity),
                description=data.description or "",
                location=data.location,
                onset_time=data.onset_time,
                duration_hours=data.duration_hours,
                triggers=data.triggers,
                relieving_factors=data.relieving_factors,
                associated_symptoms=data.associated_symptoms,
                notes=data.notes or "",
            )
            analysis = result.get("analysis", {})
        except Exception:
            pass

    return {
        "symptom_id": symptom.symptom_id,
        "analysis": analysis,
        "message": "Symptom reported successfully",
    }


@router.get("/{patient_id}", response_model=dict[str, Any])
async def get_patient_symptoms(
    patient_id: str,
    active_only: bool = True,
    limit: int = 50,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    """Get symptoms for a patient."""
    repo = SymptomRepository(db)
    symptoms = await repo.get_by_patient(patient_id, active_only, limit)

    return {
        "patient_id": patient_id,
        "symptoms": [s.model_dump() for s in symptoms],
        "count": len(symptoms),
    }


@router.get("/{patient_id}/analysis", response_model=dict[str, Any])
async def analyze_symptoms(
    patient_id: str,
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Get symptom analysis and patterns for a patient."""
    if not health_system.symptom_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Symptom agent not available"
        )

    # Get risk assessment
    assessment = health_system.symptom_agent.get_risk_assessment(patient_id)

    # Get patterns
    patterns = health_system.symptom_agent._patterns.get(patient_id, [])[-10:]

    return {
        "patient_id": patient_id,
        "risk_assessment": assessment,
        "patterns": [
            {
                "type": p.pattern_type,
                "symptoms": p.symptoms,
                "frequency": p.frequency,
                "confidence": p.confidence,
                "description": p.description,
                "recommendation": p.recommendation,
            }
            for p in patterns
        ],
    }


@router.post("/{symptom_id}/resolve", response_model=dict[str, Any])
async def resolve_symptom(
    symptom_id: str,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    """Mark a symptom as resolved."""
    repo = SymptomRepository(db)
    await repo.resolve(symptom_id)

    return {
        "message": "Symptom marked as resolved",
        "symptom_id": symptom_id,
    }


@router.get("/{patient_id}/risk", response_model=dict[str, Any])
async def get_symptom_risk(
    patient_id: str,
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Get symptom-based risk assessment."""
    if not health_system.symptom_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Symptom agent not available"
        )

    assessment = health_system.symptom_agent.get_risk_assessment(patient_id)

    return {
        "patient_id": patient_id,
        **assessment,
    }
