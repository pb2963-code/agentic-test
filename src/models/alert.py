"""Alert data models."""

import json
from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AlertCreate(BaseModel):
    """Schema for creating an alert."""

    patient_id: str
    category: str
    severity: int = Field(..., ge=1, le=5)
    title: str
    message: str
    source_agent: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class AlertModel(BaseModel):
    """Alert model."""

    alert_id: str
    patient_id: str
    category: str
    severity: int
    title: str
    message: str
    status: str = "active"
    source_agent: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None

    @classmethod
    def from_row(cls, row: Any) -> "AlertModel":
        """Create from database row."""
        data = {}
        if row["data"]:
            try:
                data = json.loads(row["data"])
            except json.JSONDecodeError:
                data = {}

        return cls(
            alert_id=row["alert_id"],
            patient_id=row["patient_id"],
            category=row["category"],
            severity=row["severity"],
            title=row["title"],
            message=row["message"],
            status=row["status"],
            source_agent=row["source_agent"],
            data=data,
            created_at=datetime.fromisoformat(row["created_at"]) if isinstance(row["created_at"], str) else row["created_at"],
            acknowledged_at=datetime.fromisoformat(row["acknowledged_at"]) if row["acknowledged_at"] and isinstance(row["acknowledged_at"], str) else row["acknowledged_at"],
            resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] and isinstance(row["resolved_at"], str) else row["resolved_at"],
        )


class AlertRepository:
    """Repository for alert operations."""

    def __init__(self, db: Any):
        self.db = db

    async def create(self, data: AlertCreate) -> AlertModel:
        """Create a new alert."""
        alert_id = str(uuid4())
        now = datetime.utcnow()

        await self.db.execute(
            """
            INSERT INTO alerts (
                alert_id, patient_id, category, severity, title,
                message, status, source_agent, data, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
            """,
            (
                alert_id, data.patient_id, data.category, data.severity,
                data.title, data.message, data.source_agent,
                json.dumps(data.data), now.isoformat()
            )
        )
        await self.db.commit()

        return await self.get_by_id(alert_id)

    async def get_by_id(self, alert_id: str) -> AlertModel | None:
        """Get alert by ID."""
        row = await self.db.fetchone(
            "SELECT * FROM alerts WHERE alert_id = ?",
            (alert_id,)
        )
        return AlertModel.from_row(row) if row else None

    async def get_active_by_patient(
        self,
        patient_id: str,
        min_severity: int | None = None
    ) -> list[AlertModel]:
        """Get active alerts for a patient."""
        query = "SELECT * FROM alerts WHERE patient_id = ? AND status = 'active'"
        params: list[Any] = [patient_id]

        if min_severity:
            query += " AND severity >= ?"
            params.append(min_severity)

        query += " ORDER BY severity DESC, created_at DESC"

        rows = await self.db.fetchall(query, tuple(params))
        return [AlertModel.from_row(row) for row in rows]

    async def get_history(
        self,
        patient_id: str,
        limit: int = 50
    ) -> list[AlertModel]:
        """Get alert history for a patient."""
        rows = await self.db.fetchall(
            """
            SELECT * FROM alerts
            WHERE patient_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (patient_id, limit)
        )
        return [AlertModel.from_row(row) for row in rows]

    async def acknowledge(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        await self.db.execute(
            """
            UPDATE alerts
            SET status = 'acknowledged', acknowledged_at = ?
            WHERE alert_id = ?
            """,
            (datetime.utcnow().isoformat(), alert_id)
        )
        await self.db.commit()
        return True

    async def resolve(self, alert_id: str) -> bool:
        """Resolve an alert."""
        await self.db.execute(
            """
            UPDATE alerts
            SET status = 'resolved', resolved_at = ?
            WHERE alert_id = ?
            """,
            (datetime.utcnow().isoformat(), alert_id)
        )
        await self.db.commit()
        return True

    async def get_active_count(self, patient_id: str) -> int:
        """Get count of active alerts."""
        row = await self.db.fetchone(
            "SELECT COUNT(*) as count FROM alerts WHERE patient_id = ? AND status = 'active'",
            (patient_id,)
        )
        return row["count"] if row else 0
