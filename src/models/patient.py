"""Patient data models."""

from datetime import date, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, EmailStr, Field


class PatientCreate(BaseModel):
    """Schema for creating a new patient."""

    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: str | None = None
    date_of_birth: date
    gender: str | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    blood_type: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None


class PatientUpdate(BaseModel):
    """Schema for updating a patient."""

    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    blood_type: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None


class PatientModel(BaseModel):
    """Patient model."""

    patient_id: str
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    date_of_birth: date
    gender: str | None = None
    height_cm: float | None = None
    weight_kg: float | None = None
    blood_type: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    created_at: datetime
    updated_at: datetime

    @property
    def age(self) -> int:
        """Calculate patient age."""
        today = date.today()
        return (
            today.year - self.date_of_birth.year -
            ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )

    @property
    def bmi(self) -> float | None:
        """Calculate BMI."""
        if self.height_cm and self.weight_kg:
            height_m = self.height_cm / 100
            return round(self.weight_kg / (height_m ** 2), 1)
        return None

    @classmethod
    def from_row(cls, row: Any) -> "PatientModel":
        """Create from database row."""
        return cls(
            patient_id=row["patient_id"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            email=row["email"],
            phone=row["phone"],
            date_of_birth=date.fromisoformat(row["date_of_birth"]) if isinstance(row["date_of_birth"], str) else row["date_of_birth"],
            gender=row["gender"],
            height_cm=row["height_cm"],
            weight_kg=row["weight_kg"],
            blood_type=row["blood_type"],
            emergency_contact_name=row["emergency_contact_name"],
            emergency_contact_phone=row["emergency_contact_phone"],
            created_at=datetime.fromisoformat(row["created_at"]) if isinstance(row["created_at"], str) else row["created_at"],
            updated_at=datetime.fromisoformat(row["updated_at"]) if isinstance(row["updated_at"], str) else row["updated_at"],
        )


class PatientRepository:
    """Repository for patient data operations."""

    def __init__(self, db: Any):
        self.db = db

    async def create(self, data: PatientCreate) -> PatientModel:
        """Create a new patient."""
        patient_id = str(uuid4())
        now = datetime.utcnow()

        await self.db.execute(
            """
            INSERT INTO patients (
                patient_id, first_name, last_name, email, phone,
                date_of_birth, gender, height_cm, weight_kg, blood_type,
                emergency_contact_name, emergency_contact_phone,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                patient_id, data.first_name, data.last_name, data.email, data.phone,
                data.date_of_birth.isoformat(), data.gender, data.height_cm, data.weight_kg,
                data.blood_type, data.emergency_contact_name, data.emergency_contact_phone,
                now.isoformat(), now.isoformat()
            )
        )
        await self.db.commit()

        return await self.get_by_id(patient_id)

    async def get_by_id(self, patient_id: str) -> PatientModel | None:
        """Get patient by ID."""
        row = await self.db.fetchone(
            "SELECT * FROM patients WHERE patient_id = ?",
            (patient_id,)
        )
        return PatientModel.from_row(row) if row else None

    async def get_by_email(self, email: str) -> PatientModel | None:
        """Get patient by email."""
        row = await self.db.fetchone(
            "SELECT * FROM patients WHERE email = ?",
            (email,)
        )
        return PatientModel.from_row(row) if row else None

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[PatientModel]:
        """Get all patients."""
        rows = await self.db.fetchall(
            "SELECT * FROM patients ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        )
        return [PatientModel.from_row(row) for row in rows]

    async def update(self, patient_id: str, data: PatientUpdate) -> PatientModel | None:
        """Update a patient."""
        updates = []
        values = []

        for field, value in data.model_dump(exclude_unset=True).items():
            if value is not None:
                updates.append(f"{field} = ?")
                values.append(value)

        if not updates:
            return await self.get_by_id(patient_id)

        updates.append("updated_at = ?")
        values.append(datetime.utcnow().isoformat())
        values.append(patient_id)

        await self.db.execute(
            f"UPDATE patients SET {', '.join(updates)} WHERE patient_id = ?",
            tuple(values)
        )
        await self.db.commit()

        return await self.get_by_id(patient_id)

    async def delete(self, patient_id: str) -> bool:
        """Delete a patient."""
        await self.db.execute(
            "DELETE FROM patients WHERE patient_id = ?",
            (patient_id,)
        )
        await self.db.commit()
        return True
