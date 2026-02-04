"""Medication data models."""

import json
from datetime import date, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class MedicationCreate(BaseModel):
    """Schema for creating a medication."""

    patient_id: str
    name: str = Field(..., min_length=1)
    dosage: str
    frequency: str
    scheduled_times: list[str] = Field(default_factory=list)
    start_date: date
    end_date: date | None = None
    instructions: str | None = None
    prescriber: str | None = None


class MedicationModel(BaseModel):
    """Medication model."""

    medication_id: str
    patient_id: str
    name: str
    dosage: str
    frequency: str
    scheduled_times: list[str]
    start_date: date
    end_date: date | None = None
    instructions: str | None = None
    prescriber: str | None = None
    is_active: bool = True
    created_at: datetime

    @classmethod
    def from_row(cls, row: Any) -> "MedicationModel":
        """Create from database row."""
        scheduled_times = []
        if row["scheduled_times"]:
            try:
                scheduled_times = json.loads(row["scheduled_times"])
            except json.JSONDecodeError:
                scheduled_times = []

        return cls(
            medication_id=row["medication_id"],
            patient_id=row["patient_id"],
            name=row["name"],
            dosage=row["dosage"],
            frequency=row["frequency"],
            scheduled_times=scheduled_times,
            start_date=date.fromisoformat(row["start_date"]) if isinstance(row["start_date"], str) else row["start_date"],
            end_date=date.fromisoformat(row["end_date"]) if row["end_date"] and isinstance(row["end_date"], str) else row["end_date"],
            instructions=row["instructions"],
            prescriber=row["prescriber"],
            is_active=bool(row["is_active"]),
            created_at=datetime.fromisoformat(row["created_at"]) if isinstance(row["created_at"], str) else row["created_at"],
        )


class DoseRecordCreate(BaseModel):
    """Schema for creating a dose record."""

    medication_id: str
    patient_id: str
    scheduled_time: datetime
    status: str  # taken, missed, skipped
    actual_time: datetime | None = None
    notes: str | None = None


class DoseRecordModel(BaseModel):
    """Dose record model."""

    record_id: str
    medication_id: str
    patient_id: str
    scheduled_time: datetime
    status: str
    actual_time: datetime | None = None
    notes: str | None = None

    @classmethod
    def from_row(cls, row: Any) -> "DoseRecordModel":
        """Create from database row."""
        return cls(
            record_id=row["record_id"],
            medication_id=row["medication_id"],
            patient_id=row["patient_id"],
            scheduled_time=datetime.fromisoformat(row["scheduled_time"]) if isinstance(row["scheduled_time"], str) else row["scheduled_time"],
            status=row["status"],
            actual_time=datetime.fromisoformat(row["actual_time"]) if row["actual_time"] and isinstance(row["actual_time"], str) else row["actual_time"],
            notes=row["notes"],
        )


class MedicationRepository:
    """Repository for medication operations."""

    def __init__(self, db: Any):
        self.db = db

    async def create(self, data: MedicationCreate) -> MedicationModel:
        """Create a new medication."""
        medication_id = str(uuid4())
        now = datetime.utcnow()

        await self.db.execute(
            """
            INSERT INTO medications (
                medication_id, patient_id, name, dosage, frequency,
                scheduled_times, start_date, end_date, instructions,
                prescriber, is_active, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                medication_id, data.patient_id, data.name, data.dosage,
                data.frequency, json.dumps(data.scheduled_times),
                data.start_date.isoformat(),
                data.end_date.isoformat() if data.end_date else None,
                data.instructions, data.prescriber, now.isoformat()
            )
        )
        await self.db.commit()

        return await self.get_by_id(medication_id)

    async def get_by_id(self, medication_id: str) -> MedicationModel | None:
        """Get medication by ID."""
        row = await self.db.fetchone(
            "SELECT * FROM medications WHERE medication_id = ?",
            (medication_id,)
        )
        return MedicationModel.from_row(row) if row else None

    async def get_by_patient(
        self,
        patient_id: str,
        active_only: bool = True
    ) -> list[MedicationModel]:
        """Get medications for a patient."""
        query = "SELECT * FROM medications WHERE patient_id = ?"
        params: list[Any] = [patient_id]

        if active_only:
            query += " AND is_active = 1"

        query += " ORDER BY name"

        rows = await self.db.fetchall(query, tuple(params))
        return [MedicationModel.from_row(row) for row in rows]

    async def deactivate(self, medication_id: str) -> bool:
        """Deactivate a medication."""
        await self.db.execute(
            "UPDATE medications SET is_active = 0 WHERE medication_id = ?",
            (medication_id,)
        )
        await self.db.commit()
        return True

    async def create_dose_record(self, data: DoseRecordCreate) -> DoseRecordModel:
        """Create a dose record."""
        record_id = str(uuid4())

        await self.db.execute(
            """
            INSERT INTO dose_records (
                record_id, medication_id, patient_id, scheduled_time,
                status, actual_time, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id, data.medication_id, data.patient_id,
                data.scheduled_time.isoformat(), data.status,
                data.actual_time.isoformat() if data.actual_time else None,
                data.notes
            )
        )
        await self.db.commit()

        row = await self.db.fetchone(
            "SELECT * FROM dose_records WHERE record_id = ?",
            (record_id,)
        )
        return DoseRecordModel.from_row(row)

    async def get_dose_records(
        self,
        patient_id: str,
        medication_id: str | None = None,
        since: datetime | None = None,
        limit: int = 100
    ) -> list[DoseRecordModel]:
        """Get dose records for a patient."""
        query = "SELECT * FROM dose_records WHERE patient_id = ?"
        params: list[Any] = [patient_id]

        if medication_id:
            query += " AND medication_id = ?"
            params.append(medication_id)

        if since:
            query += " AND scheduled_time >= ?"
            params.append(since.isoformat())

        query += " ORDER BY scheduled_time DESC LIMIT ?"
        params.append(limit)

        rows = await self.db.fetchall(query, tuple(params))
        return [DoseRecordModel.from_row(row) for row in rows]

    async def calculate_adherence(
        self,
        patient_id: str,
        days: int = 30
    ) -> dict[str, Any]:
        """Calculate medication adherence."""
        since = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        since = since.replace(day=since.day - days) if since.day > days else since

        row = await self.db.fetchone(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN status IN ('taken', 'late') THEN 1 ELSE 0 END) as taken
            FROM dose_records
            WHERE patient_id = ? AND scheduled_time >= ?
            """,
            (patient_id, since.isoformat())
        )

        if row and row["total"] > 0:
            adherence = (row["taken"] / row["total"]) * 100
            return {
                "adherence_rate": round(adherence, 1),
                "doses_taken": row["taken"],
                "doses_total": row["total"],
                "period_days": days,
            }

        return {
            "adherence_rate": 100.0,
            "doses_taken": 0,
            "doses_total": 0,
            "period_days": days,
        }
