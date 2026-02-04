"""Symptom data models."""

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class SymptomCreate(BaseModel):
    """Schema for creating a symptom."""

    patient_id: str
    name: str = Field(..., min_length=1)
    category: str | None = None
    severity: int = Field(..., ge=1, le=4)
    description: str | None = None
    location: str | None = None
    onset_time: datetime | None = None
    duration_hours: float | None = None
    triggers: list[str] = Field(default_factory=list)


class SymptomModel(BaseModel):
    """Symptom model."""

    symptom_id: str
    patient_id: str
    name: str
    category: str | None = None
    severity: int
    description: str | None = None
    location: str | None = None
    onset_time: datetime | None = None
    duration_hours: float | None = None
    triggers: list[str] = Field(default_factory=list)
    reported_at: datetime
    resolved_at: datetime | None = None

    @classmethod
    def from_row(cls, row: Any) -> "SymptomModel":
        """Create from database row."""
        triggers = []
        if row["triggers"]:
            try:
                triggers = json.loads(row["triggers"])
            except json.JSONDecodeError:
                triggers = []

        return cls(
            symptom_id=row["symptom_id"],
            patient_id=row["patient_id"],
            name=row["name"],
            category=row["category"],
            severity=row["severity"],
            description=row["description"],
            location=row["location"],
            onset_time=datetime.fromisoformat(row["onset_time"]) if row["onset_time"] and isinstance(row["onset_time"], str) else row["onset_time"],
            duration_hours=row["duration_hours"],
            triggers=triggers,
            reported_at=datetime.fromisoformat(row["reported_at"]) if isinstance(row["reported_at"], str) else row["reported_at"],
            resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] and isinstance(row["resolved_at"], str) else row["resolved_at"],
        )


class SymptomRepository:
    """Repository for symptom operations."""

    def __init__(self, db: Any):
        self.db = db

    async def create(self, data: SymptomCreate) -> SymptomModel:
        """Create a new symptom."""
        symptom_id = str(uuid4())
        now = datetime.utcnow()

        await self.db.execute(
            """
            INSERT INTO symptoms (
                symptom_id, patient_id, name, category, severity,
                description, location, onset_time, duration_hours,
                triggers, reported_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                symptom_id, data.patient_id, data.name, data.category,
                data.severity, data.description, data.location,
                data.onset_time.isoformat() if data.onset_time else None,
                data.duration_hours, json.dumps(data.triggers), now.isoformat()
            )
        )
        await self.db.commit()

        return await self.get_by_id(symptom_id)

    async def get_by_id(self, symptom_id: str) -> SymptomModel | None:
        """Get symptom by ID."""
        row = await self.db.fetchone(
            "SELECT * FROM symptoms WHERE symptom_id = ?",
            (symptom_id,)
        )
        return SymptomModel.from_row(row) if row else None

    async def get_by_patient(
        self,
        patient_id: str,
        active_only: bool = True,
        limit: int = 50
    ) -> list[SymptomModel]:
        """Get symptoms for a patient."""
        query = "SELECT * FROM symptoms WHERE patient_id = ?"
        params: list[Any] = [patient_id]

        if active_only:
            query += " AND resolved_at IS NULL"

        query += " ORDER BY reported_at DESC LIMIT ?"
        params.append(limit)

        rows = await self.db.fetchall(query, tuple(params))
        return [SymptomModel.from_row(row) for row in rows]

    async def resolve(self, symptom_id: str) -> bool:
        """Mark symptom as resolved."""
        await self.db.execute(
            "UPDATE symptoms SET resolved_at = ? WHERE symptom_id = ?",
            (datetime.utcnow().isoformat(), symptom_id)
        )
        await self.db.commit()
        return True

    async def get_recent_count(
        self,
        patient_id: str,
        days: int = 7
    ) -> int:
        """Get count of recent symptoms."""
        since = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        row = await self.db.fetchone(
            """
            SELECT COUNT(*) as count FROM symptoms
            WHERE patient_id = ? AND reported_at >= datetime(?, ?)
            """,
            (patient_id, since.isoformat(), f"-{days} days")
        )

        return row["count"] if row else 0
