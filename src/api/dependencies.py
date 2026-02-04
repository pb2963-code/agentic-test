"""API dependencies and shared resources."""

import logging
from datetime import date
from typing import Any

from ..agents import (
    AlertAgent,
    CoordinatorAgent,
    MedicationAgent,
    SymptomAnalysisAgent,
    VitalSignsAgent,
    WellnessAgent,
)
from ..core import AgentOrchestrator, PatientProfile
from ..models.database import Database, get_database
from ..models.patient import PatientRepository

logger = logging.getLogger(__name__)

# Global health system instance
_health_system: "HealthMonitoringSystem | None" = None


class HealthMonitoringSystem:
    """
    Central health monitoring system.

    Manages the multi-agent system and provides access to all agents.
    """

    def __init__(self):
        self.orchestrator = AgentOrchestrator()
        self.vital_signs_agent: VitalSignsAgent | None = None
        self.medication_agent: MedicationAgent | None = None
        self.symptom_agent: SymptomAnalysisAgent | None = None
        self.wellness_agent: WellnessAgent | None = None
        self.alert_agent: AlertAgent | None = None
        self.coordinator_agent: CoordinatorAgent | None = None
        self._started = False

    async def start(self) -> None:
        """Initialize and start the health monitoring system."""
        if self._started:
            return

        # Create agents
        self.vital_signs_agent = VitalSignsAgent()
        self.medication_agent = MedicationAgent()
        self.symptom_agent = SymptomAnalysisAgent()
        self.wellness_agent = WellnessAgent()
        self.alert_agent = AlertAgent()
        self.coordinator_agent = CoordinatorAgent()

        # Register agents with orchestrator
        self.orchestrator.register_agent(self.vital_signs_agent)
        self.orchestrator.register_agent(self.medication_agent)
        self.orchestrator.register_agent(self.symptom_agent)
        self.orchestrator.register_agent(self.wellness_agent)
        self.orchestrator.register_agent(self.alert_agent)
        self.orchestrator.register_agent(self.coordinator_agent)

        # Start orchestrator (starts all agents)
        await self.orchestrator.start()

        self._started = True
        logger.info("Health monitoring system started with all agents")

    async def stop(self) -> None:
        """Stop the health monitoring system."""
        if not self._started:
            return

        await self.orchestrator.stop()
        self._started = False
        logger.info("Health monitoring system stopped")

    def register_patient(self, profile: PatientProfile) -> None:
        """Register a patient with the system."""
        self.orchestrator.register_patient(profile)

    def get_system_status(self) -> dict[str, Any]:
        """Get overall system status."""
        return self.orchestrator.get_system_status()


async def get_health_system() -> HealthMonitoringSystem:
    """Get or create the health monitoring system."""
    global _health_system
    if _health_system is None:
        _health_system = HealthMonitoringSystem()
        await _health_system.start()

        # Load existing patients from database
        await _load_patients_to_system(_health_system)

    return _health_system


async def shutdown_health_system() -> None:
    """Shutdown the health monitoring system."""
    global _health_system
    if _health_system:
        await _health_system.stop()
        _health_system = None


async def _load_patients_to_system(system: HealthMonitoringSystem) -> None:
    """Load existing patients from database into the agent system."""
    db = await get_database()
    patient_repo = PatientRepository(db)

    patients = await patient_repo.get_all(limit=1000)

    for patient in patients:
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
        system.register_patient(profile)

    logger.info(f"Loaded {len(patients)} patients into the agent system")


async def get_db() -> Database:
    """Dependency to get database connection."""
    return await get_database()
