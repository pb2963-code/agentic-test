"""Tests for health monitoring agents."""

import pytest
from datetime import datetime, date
from unittest.mock import AsyncMock, MagicMock

from src.core import AgentOrchestrator, EventBus, PatientProfile, HealthContext
from src.agents import (
    VitalSignsAgent,
    MedicationAgent,
    SymptomAnalysisAgent,
    WellnessAgent,
    AlertAgent,
    CoordinatorAgent,
)
from src.agents.vital_signs_agent import VitalType
from src.agents.symptom_agent import SymptomSeverity
from src.agents.medication_agent import MedicationFrequency


@pytest.fixture
def patient_profile():
    """Create a test patient profile."""
    return PatientProfile(
        patient_id="test-patient-001",
        first_name="John",
        last_name="Doe",
        date_of_birth=date(1985, 5, 15),
        gender="male",
        email="john.doe@test.com",
        phone="555-1234",
        height_cm=175.0,
        weight_kg=75.0,
    )


@pytest.fixture
def health_context(patient_profile):
    """Create a test health context."""
    return HealthContext(
        patient_id=patient_profile.patient_id,
        profile=patient_profile,
    )


@pytest.fixture
def event_bus():
    """Create a test event bus."""
    return EventBus()


class TestVitalSignsAgent:
    """Tests for VitalSignsAgent."""

    @pytest.fixture
    def agent(self, event_bus, health_context):
        """Create a test vital signs agent."""
        agent = VitalSignsAgent()
        agent.set_event_bus(event_bus)
        agent.register_health_context(health_context)
        return agent

    @pytest.mark.asyncio
    async def test_record_vital_normal(self, agent):
        """Test recording a normal vital reading."""
        result = await agent.record_vital(
            patient_id="test-patient-001",
            vital_type=VitalType.HEART_RATE,
            value=72,
            unit="bpm",
        )

        assert result["status"] == "normal"
        assert result["value"] == 72
        assert result["vital_type"] == "heart_rate"

    @pytest.mark.asyncio
    async def test_record_vital_anomaly(self, agent):
        """Test recording an abnormal vital reading."""
        result = await agent.record_vital(
            patient_id="test-patient-001",
            vital_type=VitalType.HEART_RATE,
            value=160,
            unit="bpm",
        )

        assert result["status"] == "critical"
        assert result["alert_type"] == "critical"

    def test_calculate_trend_insufficient_data(self, agent):
        """Test trend calculation with insufficient data."""
        trend = agent._calculate_trend(
            "test-patient-001",
            VitalType.HEART_RATE,
        )

        assert trend["direction"] == "insufficient_data"


class TestMedicationAgent:
    """Tests for MedicationAgent."""

    @pytest.fixture
    def agent(self, event_bus, health_context):
        """Create a test medication agent."""
        agent = MedicationAgent()
        agent.set_event_bus(event_bus)
        agent.register_health_context(health_context)
        return agent

    @pytest.mark.asyncio
    async def test_add_medication(self, agent):
        """Test adding a medication."""
        from datetime import time

        result = await agent.add_medication(
            patient_id="test-patient-001",
            medication_name="Aspirin",
            dosage="100mg",
            frequency=MedicationFrequency.ONCE_DAILY,
            scheduled_times=[time(8, 0)],
            start_date=date.today(),
        )

        assert result["medication_name"] == "Aspirin"
        assert "medication_id" in result

    def test_get_upcoming_doses_empty(self, agent):
        """Test getting upcoming doses when none exist."""
        doses = agent.get_upcoming_doses("test-patient-001")
        assert doses == []

    def test_calculate_adherence_no_records(self, agent):
        """Test adherence calculation with no records."""
        adherence = agent.calculate_adherence("test-patient-001")
        assert adherence["adherence_rate"] == 100.0


class TestSymptomAnalysisAgent:
    """Tests for SymptomAnalysisAgent."""

    @pytest.fixture
    def agent(self, event_bus, health_context):
        """Create a test symptom agent."""
        agent = SymptomAnalysisAgent()
        agent.set_event_bus(event_bus)
        agent.register_health_context(health_context)
        return agent

    @pytest.mark.asyncio
    async def test_report_symptom(self, agent):
        """Test reporting a symptom."""
        result = await agent.report_symptom(
            patient_id="test-patient-001",
            symptom_name="Headache",
            severity=SymptomSeverity.MODERATE,
            description="Mild headache",
        )

        assert "symptom_id" in result
        assert "analysis" in result

    def test_get_risk_assessment_no_symptoms(self, agent):
        """Test risk assessment with no symptoms."""
        assessment = agent.get_risk_assessment("test-patient-001")
        assert assessment["overall_risk"] == "low"
        assert assessment["active_symptoms"] == 0


class TestWellnessAgent:
    """Tests for WellnessAgent."""

    @pytest.fixture
    def agent(self, event_bus, health_context):
        """Create a test wellness agent."""
        agent = WellnessAgent()
        agent.set_event_bus(event_bus)
        agent.register_health_context(health_context)
        return agent

    @pytest.mark.asyncio
    async def test_log_activity(self, agent):
        """Test logging an activity."""
        from src.agents.wellness_agent import ActivityType

        result = await agent.log_activity(
            patient_id="test-patient-001",
            activity_type=ActivityType.WALKING,
            duration_minutes=30,
        )

        assert "activity_id" in result
        assert "calories_burned" in result
        assert result["duration_minutes"] == 30

    @pytest.mark.asyncio
    async def test_log_steps(self, agent):
        """Test logging steps."""
        result = await agent.log_steps(
            patient_id="test-patient-001",
            steps=5000,
        )

        assert result["total_steps"] == 5000

    def test_get_recommendations_empty(self, agent):
        """Test getting recommendations with no data."""
        recs = agent.get_recommendations("test-patient-001")
        assert len(recs) > 0  # Should have default recommendation


class TestCoordinatorAgent:
    """Tests for CoordinatorAgent."""

    @pytest.fixture
    def agent(self, event_bus, health_context):
        """Create a test coordinator agent."""
        agent = CoordinatorAgent()
        agent.set_event_bus(event_bus)
        agent.register_health_context(health_context)
        return agent

    def test_get_dashboard_data(self, agent, patient_profile):
        """Test getting dashboard data."""
        dashboard = agent.get_dashboard_data(patient_profile.patient_id)

        assert "patient" in dashboard
        assert "vitals" in dashboard
        assert dashboard["patient"]["id"] == patient_profile.patient_id

    @pytest.mark.asyncio
    async def test_generate_health_summary(self, agent, patient_profile):
        """Test generating health summary."""
        summary = await agent.generate_health_summary(patient_profile.patient_id)

        assert summary.patient_id == patient_profile.patient_id
        assert summary.overall_status in [
            "healthy",
            "stable_with_concerns",
            "needs_attention",
            "requires_immediate_attention",
        ]


class TestAgentOrchestrator:
    """Tests for AgentOrchestrator."""

    @pytest.fixture
    def orchestrator(self):
        """Create a test orchestrator."""
        return AgentOrchestrator()

    def test_register_agent(self, orchestrator):
        """Test registering an agent."""
        agent = VitalSignsAgent()
        orchestrator.register_agent(agent)

        assert agent.agent_id in orchestrator.agents

    def test_register_patient(self, orchestrator, patient_profile):
        """Test registering a patient."""
        context = orchestrator.register_patient(patient_profile)

        assert context.patient_id == patient_profile.patient_id
        assert patient_profile.patient_id in orchestrator._health_contexts

    def test_get_system_status(self, orchestrator):
        """Test getting system status."""
        status = orchestrator.get_system_status()

        assert "running" in status
        assert "agents_count" in status
        assert "patients_count" in status
