"""Medication management routes."""

from datetime import date, datetime, time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ...agents.medication_agent import DoseStatus, MedicationFrequency
from ...models.database import Database
from ...models.medication import DoseRecordCreate, MedicationCreate, MedicationRepository
from ..dependencies import get_db, get_health_system, HealthMonitoringSystem

router = APIRouter()


class AddMedicationRequest(BaseModel):
    """Request to add a medication."""

    patient_id: str
    name: str
    dosage: str
    frequency: str = Field(..., description="Frequency (once_daily, twice_daily, etc.)")
    scheduled_times: list[str] = Field(..., description="Times in HH:MM format")
    start_date: date
    end_date: date | None = None
    instructions: str | None = None
    with_food: bool = False
    prescriber: str | None = None


class RecordDoseRequest(BaseModel):
    """Request to record a medication dose."""

    patient_id: str
    medication_id: str
    scheduled_time: datetime
    status: str = Field(..., description="Status (taken, missed, skipped)")
    actual_time: datetime | None = None
    notes: str | None = None


@router.post("/", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def add_medication(
    data: AddMedicationRequest,
    db: Database = Depends(get_db),
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """
    Add a medication to a patient's schedule.

    Checks for drug interactions with existing medications.
    """
    # Save to database
    repo = MedicationRepository(db)
    medication = await repo.create(MedicationCreate(
        patient_id=data.patient_id,
        name=data.name,
        dosage=data.dosage,
        frequency=data.frequency,
        scheduled_times=data.scheduled_times,
        start_date=data.start_date,
        end_date=data.end_date,
        instructions=data.instructions,
        prescriber=data.prescriber,
    ))

    # Process through agent for interaction checking
    interactions = []
    if health_system.medication_agent:
        try:
            scheduled_times = [time.fromisoformat(t) for t in data.scheduled_times]
            result = await health_system.medication_agent.add_medication(
                patient_id=data.patient_id,
                medication_name=data.name,
                dosage=data.dosage,
                frequency=MedicationFrequency(data.frequency),
                scheduled_times=scheduled_times,
                start_date=data.start_date,
                end_date=data.end_date,
                instructions=data.instructions or "",
                with_food=data.with_food,
                prescriber=data.prescriber or "",
            )
            interactions = result.get("interactions", [])
        except Exception:
            pass

    return {
        "medication_id": medication.medication_id,
        "message": "Medication added successfully",
        "interactions": interactions,
        "medication": medication.model_dump(),
    }


@router.get("/{patient_id}", response_model=dict[str, Any])
async def get_patient_medications(
    patient_id: str,
    active_only: bool = True,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    """Get medications for a patient."""
    repo = MedicationRepository(db)
    medications = await repo.get_by_patient(patient_id, active_only)

    return {
        "patient_id": patient_id,
        "medications": [m.model_dump() for m in medications],
        "count": len(medications),
    }


@router.get("/{patient_id}/upcoming", response_model=dict[str, Any])
async def get_upcoming_doses(
    patient_id: str,
    hours_ahead: int = 24,
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Get upcoming medication doses."""
    if not health_system.medication_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Medication agent not available"
        )

    upcoming = health_system.medication_agent.get_upcoming_doses(
        patient_id, hours_ahead
    )

    return {
        "patient_id": patient_id,
        "hours_ahead": hours_ahead,
        "upcoming_doses": upcoming,
    }


@router.post("/dose", response_model=dict[str, Any])
async def record_dose(
    data: RecordDoseRequest,
    db: Database = Depends(get_db),
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Record a medication dose."""
    # Save to database
    repo = MedicationRepository(db)
    record = await repo.create_dose_record(DoseRecordCreate(
        medication_id=data.medication_id,
        patient_id=data.patient_id,
        scheduled_time=data.scheduled_time,
        status=data.status,
        actual_time=data.actual_time,
        notes=data.notes,
    ))

    # Process through agent
    if health_system.medication_agent:
        try:
            await health_system.medication_agent.record_dose(
                patient_id=data.patient_id,
                medication_id=data.medication_id,
                status=DoseStatus(data.status),
                scheduled_time=data.scheduled_time,
                actual_time=data.actual_time,
                notes=data.notes or "",
            )
        except Exception:
            pass

    return {
        "record_id": record.record_id,
        "message": f"Dose recorded as {data.status}",
    }


@router.get("/{patient_id}/adherence", response_model=dict[str, Any])
async def get_adherence(
    patient_id: str,
    days: int = 30,
    db: Database = Depends(get_db),
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Get medication adherence statistics."""
    repo = MedicationRepository(db)
    adherence = await repo.calculate_adherence(patient_id, days)

    # Get agent-based adherence if available
    agent_adherence = None
    if health_system.medication_agent:
        agent_adherence = health_system.medication_agent.calculate_adherence(
            patient_id, days
        )

    return {
        "patient_id": patient_id,
        "adherence": adherence,
        "detailed": agent_adherence,
    }


@router.post("/{medication_id}/deactivate", response_model=dict[str, Any])
async def deactivate_medication(
    medication_id: str,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    """Deactivate a medication."""
    repo = MedicationRepository(db)
    await repo.deactivate(medication_id)

    return {
        "message": "Medication deactivated",
        "medication_id": medication_id,
    }


@router.post("/check-interactions", response_model=dict[str, Any])
async def check_interactions(
    patient_id: str,
    medication_name: str,
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Check for drug interactions."""
    if not health_system.medication_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Medication agent not available"
        )

    interactions = health_system.medication_agent._check_interactions(
        patient_id, medication_name
    )

    return {
        "medication": medication_name,
        "interactions": [
            {
                "with": i.medication_2,
                "severity": i.severity,
                "description": i.description,
                "recommendation": i.recommendation,
            }
            for i in interactions
        ],
    }
