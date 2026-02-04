"""Patient management routes."""

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from ...core import PatientProfile
from ...models.database import Database
from ...models.patient import PatientCreate, PatientModel, PatientRepository, PatientUpdate
from ..dependencies import get_db, get_health_system, HealthMonitoringSystem

router = APIRouter()


@router.post("/", response_model=dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_patient(
    data: PatientCreate,
    db: Database = Depends(get_db),
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """
    Register a new patient.

    Creates a patient profile and registers them with the health monitoring system.
    """
    repo = PatientRepository(db)

    # Check if email already exists
    existing = await repo.get_by_email(data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A patient with this email already exists"
        )

    # Create patient in database
    patient = await repo.create(data)

    # Register with health monitoring system
    profile = PatientProfile(
        patient_id=patient.patient_id,
        first_name=patient.first_name,
        last_name=patient.last_name,
        date_of_birth=patient.date_of_birth,
        gender=patient.gender or "unknown",
        email=patient.email,
        phone=patient.phone or "",
        height_cm=patient.height_cm,
        weight_kg=patient.weight_kg,
    )
    health_system.register_patient(profile)

    return {
        "patient_id": patient.patient_id,
        "message": "Patient registered successfully",
        "patient": patient.model_dump(),
    }


@router.get("/{patient_id}", response_model=dict[str, Any])
async def get_patient(
    patient_id: str,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    """Get patient by ID."""
    repo = PatientRepository(db)
    patient = await repo.get_by_id(patient_id)

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )

    return {
        "patient": patient.model_dump(),
        "computed": {
            "age": patient.age,
            "bmi": patient.bmi,
        },
    }


@router.get("/", response_model=dict[str, Any])
async def list_patients(
    limit: int = 100,
    offset: int = 0,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    """List all patients."""
    repo = PatientRepository(db)
    patients = await repo.get_all(limit=limit, offset=offset)

    return {
        "patients": [p.model_dump() for p in patients],
        "count": len(patients),
    }


@router.patch("/{patient_id}", response_model=dict[str, Any])
async def update_patient(
    patient_id: str,
    data: PatientUpdate,
    db: Database = Depends(get_db),
) -> dict[str, Any]:
    """Update patient information."""
    repo = PatientRepository(db)

    patient = await repo.get_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )

    updated = await repo.update(patient_id, data)

    return {
        "message": "Patient updated successfully",
        "patient": updated.model_dump() if updated else None,
    }


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: str,
    db: Database = Depends(get_db),
) -> None:
    """Delete a patient."""
    repo = PatientRepository(db)

    patient = await repo.get_by_id(patient_id)
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )

    await repo.delete(patient_id)
