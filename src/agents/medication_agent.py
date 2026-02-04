"""Medication management agent."""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

from ..core.base_agent import AgentCapability, BaseAgent
from ..core.event_bus import Event, EventType
from ..core.message import Message

logger = logging.getLogger(__name__)


class MedicationFrequency(Enum):
    """Medication frequency options."""

    ONCE_DAILY = "once_daily"
    TWICE_DAILY = "twice_daily"
    THREE_TIMES_DAILY = "three_times_daily"
    FOUR_TIMES_DAILY = "four_times_daily"
    EVERY_OTHER_DAY = "every_other_day"
    WEEKLY = "weekly"
    AS_NEEDED = "as_needed"
    CUSTOM = "custom"


class DoseStatus(Enum):
    """Status of a medication dose."""

    PENDING = "pending"
    TAKEN = "taken"
    MISSED = "missed"
    SKIPPED = "skipped"
    LATE = "late"


@dataclass
class MedicationSchedule:
    """Schedule for a medication."""

    medication_id: str
    patient_id: str
    medication_name: str
    dosage: str
    frequency: MedicationFrequency
    scheduled_times: list[time]
    start_date: date
    end_date: date | None = None
    instructions: str = ""
    with_food: bool = False
    interactions: list[str] = field(default_factory=list)
    side_effects: list[str] = field(default_factory=list)
    prescriber: str = ""
    pharmacy: str = ""
    refill_date: date | None = None
    quantity_remaining: int | None = None
    is_active: bool = True


@dataclass
class DoseRecord:
    """Record of a single dose."""

    record_id: str
    medication_id: str
    patient_id: str
    scheduled_time: datetime
    status: DoseStatus
    actual_time: datetime | None = None
    notes: str = ""


@dataclass
class InteractionWarning:
    """Drug interaction warning."""

    medication_1: str
    medication_2: str
    severity: str  # mild, moderate, severe
    description: str
    recommendation: str


# Common drug interactions database (simplified)
KNOWN_INTERACTIONS: list[dict[str, Any]] = [
    {
        "drugs": ["warfarin", "aspirin"],
        "severity": "severe",
        "description": "Increased risk of bleeding",
        "recommendation": "Monitor closely or avoid combination"
    },
    {
        "drugs": ["metformin", "alcohol"],
        "severity": "moderate",
        "description": "Risk of lactic acidosis",
        "recommendation": "Limit alcohol consumption"
    },
    {
        "drugs": ["lisinopril", "potassium"],
        "severity": "moderate",
        "description": "Risk of hyperkalemia",
        "recommendation": "Monitor potassium levels"
    },
    {
        "drugs": ["simvastatin", "grapefruit"],
        "severity": "moderate",
        "description": "Increased drug concentration",
        "recommendation": "Avoid grapefruit products"
    },
]


class MedicationAgent(BaseAgent):
    """
    Agent responsible for medication management.

    Capabilities:
    - Medication schedule management
    - Dose tracking and reminders
    - Drug interaction checking
    - Refill reminders
    - Adherence monitoring
    """

    def __init__(self, agent_id: str | None = None):
        super().__init__(
            agent_id=agent_id,
            name="MedicationAgent",
            description="Manages medication schedules, reminders, and interactions",
            capabilities=[
                AgentCapability.MEDICATION_MANAGEMENT,
                AgentCapability.RECOMMENDATION,
            ]
        )

        # Medication schedules (patient_id -> medication_id -> schedule)
        self._schedules: dict[str, dict[str, MedicationSchedule]] = {}

        # Dose records (patient_id -> list of records)
        self._dose_records: dict[str, list[DoseRecord]] = {}

        # Pending reminders (reminder_id -> reminder_data)
        self._pending_reminders: dict[str, dict[str, Any]] = {}

        # Subscribe to events
        self.subscribe_to_event(EventType.MEDICATION_TAKEN)
        self.subscribe_to_event(EventType.SYSTEM_STATUS)

    async def on_start(self) -> None:
        """Initialize agent."""
        logger.info(f"{self.name} started - managing medications")

    async def handle_message(self, message: Message) -> Message | None:
        """Handle incoming messages."""
        content = message.content
        action = content.get("action")

        handlers = {
            "add_medication": self._handle_add_medication,
            "remove_medication": self._handle_remove_medication,
            "get_schedule": self._handle_get_schedule,
            "record_dose": self._handle_record_dose,
            "check_interactions": self._handle_check_interactions,
            "get_adherence": self._handle_get_adherence,
            "get_upcoming_doses": self._handle_get_upcoming_doses,
            "update_medication": self._handle_update_medication,
        }

        handler = handlers.get(action)
        if handler:
            return await handler(message)

        return message.create_response(
            self.agent_id,
            {"error": f"Unknown action: {action}"}
        )

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events."""
        if event.event_type == EventType.MEDICATION_TAKEN:
            await self._process_medication_taken(event)

    async def add_medication(
        self,
        patient_id: str,
        medication_name: str,
        dosage: str,
        frequency: MedicationFrequency,
        scheduled_times: list[time],
        start_date: date,
        end_date: date | None = None,
        instructions: str = "",
        with_food: bool = False,
        prescriber: str = "",
    ) -> dict[str, Any]:
        """
        Add a new medication to a patient's schedule.

        Returns:
            Medication info including any interaction warnings
        """
        medication_id = str(uuid4())

        schedule = MedicationSchedule(
            medication_id=medication_id,
            patient_id=patient_id,
            medication_name=medication_name,
            dosage=dosage,
            frequency=frequency,
            scheduled_times=scheduled_times,
            start_date=start_date,
            end_date=end_date,
            instructions=instructions,
            with_food=with_food,
            prescriber=prescriber,
        )

        if patient_id not in self._schedules:
            self._schedules[patient_id] = {}

        self._schedules[patient_id][medication_id] = schedule

        # Check for interactions with existing medications
        interactions = self._check_interactions(patient_id, medication_name)

        # Update schedule interactions
        if interactions:
            schedule.interactions = [
                f"{i.medication_2}: {i.description}" for i in interactions
            ]

            # Publish interaction warning
            await self._publish_event(
                EventType.MEDICATION_INTERACTION,
                {
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
                },
                patient_id=patient_id,
                tags=["interaction", medication_name.lower()]
            )

        logger.info(f"Added medication {medication_name} for patient {patient_id}")

        return {
            "medication_id": medication_id,
            "medication_name": medication_name,
            "schedule": {
                "frequency": frequency.value,
                "times": [t.isoformat() for t in scheduled_times],
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat() if end_date else None,
            },
            "interactions": [
                {
                    "with": i.medication_2,
                    "severity": i.severity,
                    "description": i.description,
                }
                for i in interactions
            ],
        }

    def _check_interactions(
        self,
        patient_id: str,
        new_medication: str
    ) -> list[InteractionWarning]:
        """Check for drug interactions with existing medications."""
        warnings = []
        new_med_lower = new_medication.lower()

        # Get current medications
        current_meds = []
        if patient_id in self._schedules:
            for schedule in self._schedules[patient_id].values():
                if schedule.is_active:
                    current_meds.append(schedule.medication_name.lower())

        # Check against known interactions
        for interaction in KNOWN_INTERACTIONS:
            drugs = [d.lower() for d in interaction["drugs"]]

            if new_med_lower in drugs:
                for med in current_meds:
                    if med in drugs and med != new_med_lower:
                        warnings.append(InteractionWarning(
                            medication_1=new_medication,
                            medication_2=med,
                            severity=interaction["severity"],
                            description=interaction["description"],
                            recommendation=interaction["recommendation"],
                        ))

        return warnings

    async def record_dose(
        self,
        patient_id: str,
        medication_id: str,
        status: DoseStatus,
        scheduled_time: datetime,
        actual_time: datetime | None = None,
        notes: str = ""
    ) -> dict[str, Any]:
        """Record a medication dose."""
        record = DoseRecord(
            record_id=str(uuid4()),
            medication_id=medication_id,
            patient_id=patient_id,
            scheduled_time=scheduled_time,
            status=status,
            actual_time=actual_time or datetime.utcnow(),
            notes=notes,
        )

        if patient_id not in self._dose_records:
            self._dose_records[patient_id] = []

        self._dose_records[patient_id].append(record)

        # Publish appropriate event
        if status == DoseStatus.TAKEN:
            await self._publish_event(
                EventType.MEDICATION_TAKEN,
                {
                    "medication_id": medication_id,
                    "scheduled_time": scheduled_time.isoformat(),
                    "actual_time": record.actual_time.isoformat() if record.actual_time else None,
                },
                patient_id=patient_id
            )
        elif status == DoseStatus.MISSED:
            await self._publish_event(
                EventType.MEDICATION_MISSED,
                {
                    "medication_id": medication_id,
                    "scheduled_time": scheduled_time.isoformat(),
                },
                patient_id=patient_id,
                tags=["missed", "adherence"]
            )

        return {
            "record_id": record.record_id,
            "status": status.value,
            "recorded_at": record.actual_time.isoformat() if record.actual_time else None,
        }

    def get_upcoming_doses(
        self,
        patient_id: str,
        hours_ahead: int = 24
    ) -> list[dict[str, Any]]:
        """Get upcoming medication doses for a patient."""
        upcoming = []
        now = datetime.utcnow()
        cutoff = now + timedelta(hours=hours_ahead)
        today = now.date()

        if patient_id not in self._schedules:
            return []

        for schedule in self._schedules[patient_id].values():
            if not schedule.is_active:
                continue

            if schedule.end_date and schedule.end_date < today:
                continue

            if schedule.start_date > today:
                continue

            for scheduled_time in schedule.scheduled_times:
                dose_datetime = datetime.combine(today, scheduled_time)

                # If time has passed today, check tomorrow
                if dose_datetime < now:
                    dose_datetime = datetime.combine(
                        today + timedelta(days=1),
                        scheduled_time
                    )

                if dose_datetime <= cutoff:
                    upcoming.append({
                        "medication_id": schedule.medication_id,
                        "medication_name": schedule.medication_name,
                        "dosage": schedule.dosage,
                        "scheduled_time": dose_datetime.isoformat(),
                        "instructions": schedule.instructions,
                        "with_food": schedule.with_food,
                    })

        # Sort by scheduled time
        upcoming.sort(key=lambda x: x["scheduled_time"])

        return upcoming

    def calculate_adherence(
        self,
        patient_id: str,
        days: int = 30
    ) -> dict[str, Any]:
        """Calculate medication adherence for a patient."""
        if patient_id not in self._dose_records:
            return {"adherence_rate": 100.0, "message": "No records yet"}

        cutoff = datetime.utcnow() - timedelta(days=days)
        records = [
            r for r in self._dose_records[patient_id]
            if r.scheduled_time >= cutoff
        ]

        if not records:
            return {"adherence_rate": 100.0, "message": "No records in period"}

        taken = sum(1 for r in records if r.status in [DoseStatus.TAKEN, DoseStatus.LATE])
        total = len(records)

        adherence_rate = (taken / total) * 100 if total > 0 else 100.0

        # Per-medication breakdown
        by_medication: dict[str, dict[str, int]] = {}
        for record in records:
            med_id = record.medication_id
            if med_id not in by_medication:
                by_medication[med_id] = {"taken": 0, "total": 0}

            by_medication[med_id]["total"] += 1
            if record.status in [DoseStatus.TAKEN, DoseStatus.LATE]:
                by_medication[med_id]["taken"] += 1

        medication_adherence = {}
        for med_id, counts in by_medication.items():
            if patient_id in self._schedules and med_id in self._schedules[patient_id]:
                med_name = self._schedules[patient_id][med_id].medication_name
            else:
                med_name = med_id

            rate = (counts["taken"] / counts["total"]) * 100 if counts["total"] > 0 else 100.0
            medication_adherence[med_name] = round(rate, 1)

        return {
            "adherence_rate": round(adherence_rate, 1),
            "period_days": days,
            "doses_taken": taken,
            "doses_total": total,
            "by_medication": medication_adherence,
        }

    async def _handle_add_medication(self, message: Message) -> Message:
        """Handle add medication request."""
        content = message.content
        try:
            scheduled_times = [
                time.fromisoformat(t) for t in content.get("scheduled_times", [])
            ]

            result = await self.add_medication(
                patient_id=content["patient_id"],
                medication_name=content["medication_name"],
                dosage=content["dosage"],
                frequency=MedicationFrequency(content["frequency"]),
                scheduled_times=scheduled_times,
                start_date=date.fromisoformat(content["start_date"]),
                end_date=date.fromisoformat(content["end_date"]) if content.get("end_date") else None,
                instructions=content.get("instructions", ""),
                with_food=content.get("with_food", False),
                prescriber=content.get("prescriber", ""),
            )
            return message.create_response(self.agent_id, {"success": True, **result})
        except Exception as e:
            return message.create_response(self.agent_id, {"success": False, "error": str(e)})

    async def _handle_remove_medication(self, message: Message) -> Message:
        """Handle remove medication request."""
        content = message.content
        patient_id = content.get("patient_id")
        medication_id = content.get("medication_id")

        if patient_id in self._schedules and medication_id in self._schedules[patient_id]:
            self._schedules[patient_id][medication_id].is_active = False
            return message.create_response(
                self.agent_id,
                {"success": True, "message": "Medication deactivated"}
            )

        return message.create_response(
            self.agent_id,
            {"success": False, "error": "Medication not found"}
        )

    async def _handle_get_schedule(self, message: Message) -> Message:
        """Handle get schedule request."""
        patient_id = message.content.get("patient_id")

        if patient_id not in self._schedules:
            return message.create_response(
                self.agent_id,
                {"success": True, "medications": []}
            )

        medications = []
        for schedule in self._schedules[patient_id].values():
            if schedule.is_active:
                medications.append({
                    "medication_id": schedule.medication_id,
                    "medication_name": schedule.medication_name,
                    "dosage": schedule.dosage,
                    "frequency": schedule.frequency.value,
                    "scheduled_times": [t.isoformat() for t in schedule.scheduled_times],
                    "instructions": schedule.instructions,
                    "with_food": schedule.with_food,
                    "interactions": schedule.interactions,
                })

        return message.create_response(
            self.agent_id,
            {"success": True, "medications": medications}
        )

    async def _handle_record_dose(self, message: Message) -> Message:
        """Handle record dose request."""
        content = message.content
        try:
            result = await self.record_dose(
                patient_id=content["patient_id"],
                medication_id=content["medication_id"],
                status=DoseStatus(content["status"]),
                scheduled_time=datetime.fromisoformat(content["scheduled_time"]),
                actual_time=datetime.fromisoformat(content["actual_time"]) if content.get("actual_time") else None,
                notes=content.get("notes", ""),
            )
            return message.create_response(self.agent_id, {"success": True, **result})
        except Exception as e:
            return message.create_response(self.agent_id, {"success": False, "error": str(e)})

    async def _handle_check_interactions(self, message: Message) -> Message:
        """Handle check interactions request."""
        content = message.content
        patient_id = content.get("patient_id")
        medication_name = content.get("medication_name")

        interactions = self._check_interactions(patient_id, medication_name)

        return message.create_response(
            self.agent_id,
            {
                "success": True,
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
        )

    async def _handle_get_adherence(self, message: Message) -> Message:
        """Handle get adherence request."""
        content = message.content
        patient_id = content.get("patient_id")
        days = content.get("days", 30)

        adherence = self.calculate_adherence(patient_id, days)
        return message.create_response(self.agent_id, {"success": True, **adherence})

    async def _handle_get_upcoming_doses(self, message: Message) -> Message:
        """Handle get upcoming doses request."""
        content = message.content
        patient_id = content.get("patient_id")
        hours_ahead = content.get("hours_ahead", 24)

        upcoming = self.get_upcoming_doses(patient_id, hours_ahead)
        return message.create_response(
            self.agent_id,
            {"success": True, "upcoming_doses": upcoming}
        )

    async def _handle_update_medication(self, message: Message) -> Message:
        """Handle update medication request."""
        content = message.content
        patient_id = content.get("patient_id")
        medication_id = content.get("medication_id")
        updates = content.get("updates", {})

        if patient_id not in self._schedules:
            return message.create_response(
                self.agent_id,
                {"success": False, "error": "Patient not found"}
            )

        if medication_id not in self._schedules[patient_id]:
            return message.create_response(
                self.agent_id,
                {"success": False, "error": "Medication not found"}
            )

        schedule = self._schedules[patient_id][medication_id]

        if "dosage" in updates:
            schedule.dosage = updates["dosage"]
        if "instructions" in updates:
            schedule.instructions = updates["instructions"]
        if "refill_date" in updates:
            schedule.refill_date = date.fromisoformat(updates["refill_date"])
        if "quantity_remaining" in updates:
            schedule.quantity_remaining = updates["quantity_remaining"]

        return message.create_response(
            self.agent_id,
            {"success": True, "message": "Medication updated"}
        )

    async def _process_medication_taken(self, event: Event) -> None:
        """Process medication taken event."""
        # Could trigger adherence recalculation or streak tracking
        logger.debug(f"Medication taken event processed for patient {event.patient_id}")
