"""Health context and patient profile management."""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any


class BloodType(Enum):
    """Blood type classification."""

    A_POSITIVE = "A+"
    A_NEGATIVE = "A-"
    B_POSITIVE = "B+"
    B_NEGATIVE = "B-"
    AB_POSITIVE = "AB+"
    AB_NEGATIVE = "AB-"
    O_POSITIVE = "O+"
    O_NEGATIVE = "O-"
    UNKNOWN = "unknown"


class RiskLevel(Enum):
    """Health risk level classification."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class EmergencyContact:
    """Emergency contact information."""

    name: str
    relationship: str
    phone: str
    email: str | None = None
    is_primary: bool = False


@dataclass
class MedicalCondition:
    """Medical condition record."""

    name: str
    diagnosed_date: date | None = None
    status: str = "active"  # active, managed, resolved
    severity: str = "moderate"
    notes: str = ""


@dataclass
class Allergy:
    """Allergy information."""

    allergen: str
    reaction_type: str
    severity: str  # mild, moderate, severe
    notes: str = ""


@dataclass
class Medication:
    """Current medication information."""

    name: str
    dosage: str
    frequency: str
    start_date: date
    end_date: date | None = None
    prescriber: str = ""
    purpose: str = ""
    instructions: str = ""
    refill_date: date | None = None


@dataclass
class PatientProfile:
    """
    Comprehensive patient profile.

    Contains all relevant health information for a patient
    that agents need to provide personalized monitoring.
    """

    patient_id: str
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    email: str
    phone: str

    # Physical attributes
    height_cm: float | None = None
    weight_kg: float | None = None
    blood_type: BloodType = BloodType.UNKNOWN

    # Medical history
    conditions: list[MedicalCondition] = field(default_factory=list)
    allergies: list[Allergy] = field(default_factory=list)
    medications: list[Medication] = field(default_factory=list)
    surgical_history: list[str] = field(default_factory=list)
    family_history: dict[str, list[str]] = field(default_factory=dict)

    # Lifestyle factors
    smoking_status: str = "never"  # never, former, current
    alcohol_consumption: str = "none"  # none, moderate, heavy
    exercise_frequency: str = "moderate"  # sedentary, light, moderate, active
    diet_type: str = "regular"

    # Emergency contacts
    emergency_contacts: list[EmergencyContact] = field(default_factory=list)

    # Healthcare providers
    primary_physician: str = ""
    specialists: list[str] = field(default_factory=list)

    # Preferences
    notification_preferences: dict[str, bool] = field(default_factory=dict)
    language: str = "en"
    timezone: str = "UTC"

    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

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
        """Calculate BMI if height and weight are available."""
        if self.height_cm and self.weight_kg:
            height_m = self.height_cm / 100
            return round(self.weight_kg / (height_m ** 2), 1)
        return None

    @property
    def active_medications(self) -> list[Medication]:
        """Get list of active medications."""
        today = date.today()
        return [
            m for m in self.medications
            if m.end_date is None or m.end_date >= today
        ]

    @property
    def active_conditions(self) -> list[MedicalCondition]:
        """Get list of active medical conditions."""
        return [c for c in self.conditions if c.status == "active"]

    def to_dict(self) -> dict[str, Any]:
        """Convert profile to dictionary."""
        return {
            "patient_id": self.patient_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "date_of_birth": self.date_of_birth.isoformat(),
            "age": self.age,
            "gender": self.gender,
            "email": self.email,
            "phone": self.phone,
            "height_cm": self.height_cm,
            "weight_kg": self.weight_kg,
            "bmi": self.bmi,
            "blood_type": self.blood_type.value,
            "conditions": [
                {"name": c.name, "status": c.status, "severity": c.severity}
                for c in self.conditions
            ],
            "allergies": [
                {"allergen": a.allergen, "severity": a.severity}
                for a in self.allergies
            ],
            "active_medications": [
                {"name": m.name, "dosage": m.dosage, "frequency": m.frequency}
                for m in self.active_medications
            ],
            "emergency_contacts": [
                {"name": c.name, "phone": c.phone, "relationship": c.relationship}
                for c in self.emergency_contacts
            ],
        }


@dataclass
class HealthContext:
    """
    Current health context for a patient.

    Aggregates real-time health data and state that agents
    use for decision making and analysis.
    """

    patient_id: str
    profile: PatientProfile

    # Current vital signs (most recent readings)
    current_vitals: dict[str, Any] = field(default_factory=dict)

    # Recent symptoms
    active_symptoms: list[dict[str, Any]] = field(default_factory=list)

    # Today's wellness data
    wellness_data: dict[str, Any] = field(default_factory=dict)

    # Active alerts
    active_alerts: list[dict[str, Any]] = field(default_factory=list)

    # Risk assessments
    risk_levels: dict[str, RiskLevel] = field(default_factory=dict)

    # Agent insights
    insights: list[dict[str, Any]] = field(default_factory=list)

    # Recommendations
    recommendations: list[dict[str, Any]] = field(default_factory=list)

    # Context metadata
    last_updated: datetime = field(default_factory=datetime.utcnow)
    data_freshness: dict[str, datetime] = field(default_factory=dict)

    def update_vitals(self, vital_type: str, value: Any, timestamp: datetime) -> None:
        """Update a vital sign reading."""
        self.current_vitals[vital_type] = {
            "value": value,
            "timestamp": timestamp.isoformat(),
        }
        self.data_freshness["vitals"] = timestamp
        self.last_updated = datetime.utcnow()

    def add_symptom(self, symptom: dict[str, Any]) -> None:
        """Add an active symptom."""
        self.active_symptoms.append(symptom)
        self.data_freshness["symptoms"] = datetime.utcnow()
        self.last_updated = datetime.utcnow()

    def add_alert(self, alert: dict[str, Any]) -> None:
        """Add an active alert."""
        self.active_alerts.append(alert)
        self.last_updated = datetime.utcnow()

    def clear_alert(self, alert_id: str) -> None:
        """Clear an alert by ID."""
        self.active_alerts = [a for a in self.active_alerts if a.get("id") != alert_id]
        self.last_updated = datetime.utcnow()

    def update_risk_level(self, category: str, level: RiskLevel) -> None:
        """Update risk level for a category."""
        self.risk_levels[category] = level
        self.last_updated = datetime.utcnow()

    def add_insight(self, insight: dict[str, Any]) -> None:
        """Add a health insight."""
        self.insights.append(insight)
        # Keep only last 50 insights
        if len(self.insights) > 50:
            self.insights = self.insights[-50:]
        self.last_updated = datetime.utcnow()

    def add_recommendation(self, recommendation: dict[str, Any]) -> None:
        """Add a health recommendation."""
        self.recommendations.append(recommendation)
        if len(self.recommendations) > 20:
            self.recommendations = self.recommendations[-20:]
        self.last_updated = datetime.utcnow()

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of current health context."""
        return {
            "patient_id": self.patient_id,
            "patient_name": f"{self.profile.first_name} {self.profile.last_name}",
            "current_vitals": self.current_vitals,
            "active_symptoms_count": len(self.active_symptoms),
            "active_alerts_count": len(self.active_alerts),
            "risk_levels": {k: v.value for k, v in self.risk_levels.items()},
            "recent_insights": self.insights[-5:] if self.insights else [],
            "recommendations_count": len(self.recommendations),
            "last_updated": self.last_updated.isoformat(),
        }
