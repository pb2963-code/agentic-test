"""Vital reading data models."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class VitalReadingCreate(BaseModel):
    """Schema for creating a vital reading."""

    patient_id: str
    vital_type: str = Field(..., description="Type of vital sign")
    value: float = Field(..., description="Reading value")
    unit: str = Field(..., description="Unit of measurement")
    device_id: str | None = None
    notes: str | None = None


class VitalReadingModel(BaseModel):
    """Vital reading model."""

    reading_id: str
    patient_id: str
    vital_type: str
    value: float
    unit: str
    device_id: str | None = None
    notes: str | None = None
    recorded_at: datetime

    @classmethod
    def from_row(cls, row: Any) -> "VitalReadingModel":
        """Create from database row."""
        return cls(
            reading_id=row["reading_id"],
            patient_id=row["patient_id"],
            vital_type=row["vital_type"],
            value=row["value"],
            unit=row["unit"],
            device_id=row["device_id"],
            notes=row["notes"],
            recorded_at=datetime.fromisoformat(row["recorded_at"]) if isinstance(row["recorded_at"], str) else row["recorded_at"],
        )


class VitalReadingRepository:
    """Repository for vital reading operations."""

    def __init__(self, db: Any):
        self.db = db

    async def create(self, data: VitalReadingCreate) -> VitalReadingModel:
        """Create a new vital reading."""
        reading_id = str(uuid4())
        now = datetime.utcnow()

        await self.db.execute(
            """
            INSERT INTO vital_readings (
                reading_id, patient_id, vital_type, value, unit,
                device_id, notes, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reading_id, data.patient_id, data.vital_type, data.value,
                data.unit, data.device_id, data.notes, now.isoformat()
            )
        )
        await self.db.commit()

        return await self.get_by_id(reading_id)

    async def get_by_id(self, reading_id: str) -> VitalReadingModel | None:
        """Get reading by ID."""
        row = await self.db.fetchone(
            "SELECT * FROM vital_readings WHERE reading_id = ?",
            (reading_id,)
        )
        return VitalReadingModel.from_row(row) if row else None

    async def get_by_patient(
        self,
        patient_id: str,
        vital_type: str | None = None,
        limit: int = 100,
        since: datetime | None = None
    ) -> list[VitalReadingModel]:
        """Get readings for a patient."""
        query = "SELECT * FROM vital_readings WHERE patient_id = ?"
        params: list[Any] = [patient_id]

        if vital_type:
            query += " AND vital_type = ?"
            params.append(vital_type)

        if since:
            query += " AND recorded_at >= ?"
            params.append(since.isoformat())

        query += " ORDER BY recorded_at DESC LIMIT ?"
        params.append(limit)

        rows = await self.db.fetchall(query, tuple(params))
        return [VitalReadingModel.from_row(row) for row in rows]

    async def get_latest(
        self,
        patient_id: str,
        vital_type: str
    ) -> VitalReadingModel | None:
        """Get latest reading of a type for a patient."""
        row = await self.db.fetchone(
            """
            SELECT * FROM vital_readings
            WHERE patient_id = ? AND vital_type = ?
            ORDER BY recorded_at DESC LIMIT 1
            """,
            (patient_id, vital_type)
        )
        return VitalReadingModel.from_row(row) if row else None

    async def get_statistics(
        self,
        patient_id: str,
        vital_type: str,
        since: datetime
    ) -> dict[str, Any]:
        """Get statistics for a vital type."""
        row = await self.db.fetchone(
            """
            SELECT
                AVG(value) as avg_value,
                MIN(value) as min_value,
                MAX(value) as max_value,
                COUNT(*) as count
            FROM vital_readings
            WHERE patient_id = ? AND vital_type = ? AND recorded_at >= ?
            """,
            (patient_id, vital_type, since.isoformat())
        )

        if row:
            return {
                "average": round(row["avg_value"], 2) if row["avg_value"] else None,
                "minimum": row["min_value"],
                "maximum": row["max_value"],
                "count": row["count"],
            }
        return {"average": None, "minimum": None, "maximum": None, "count": 0}
