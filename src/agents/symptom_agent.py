"""Symptom analysis agent."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

from ..core.base_agent import AgentCapability, BaseAgent
from ..core.context import RiskLevel
from ..core.event_bus import Event, EventType
from ..core.message import Message

logger = logging.getLogger(__name__)


class SymptomSeverity(Enum):
    """Severity levels for symptoms."""

    MILD = 1
    MODERATE = 2
    SEVERE = 3
    CRITICAL = 4


class SymptomCategory(Enum):
    """Categories of symptoms."""

    PAIN = "pain"
    RESPIRATORY = "respiratory"
    CARDIOVASCULAR = "cardiovascular"
    GASTROINTESTINAL = "gastrointestinal"
    NEUROLOGICAL = "neurological"
    MUSCULOSKELETAL = "musculoskeletal"
    DERMATOLOGICAL = "dermatological"
    PSYCHOLOGICAL = "psychological"
    GENERAL = "general"
    OTHER = "other"


@dataclass
class SymptomReport:
    """A reported symptom."""

    symptom_id: str
    patient_id: str
    symptom_name: str
    category: SymptomCategory
    severity: SymptomSeverity
    description: str
    location: str | None
    onset_time: datetime
    duration_hours: float | None
    triggers: list[str] = field(default_factory=list)
    relieving_factors: list[str] = field(default_factory=list)
    associated_symptoms: list[str] = field(default_factory=list)
    reported_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: datetime | None = None
    notes: str = ""


@dataclass
class SymptomPattern:
    """Detected pattern in symptoms."""

    pattern_id: str
    patient_id: str
    pattern_type: str
    symptoms: list[str]
    frequency: str
    confidence: float
    description: str
    recommendation: str
    detected_at: datetime = field(default_factory=datetime.utcnow)


# Symptom analysis rules (simplified knowledge base)
SYMPTOM_CORRELATIONS: dict[str, dict[str, Any]] = {
    "chest_pain": {
        "category": SymptomCategory.CARDIOVASCULAR,
        "risk_level": RiskLevel.HIGH,
        "associated": ["shortness_of_breath", "sweating", "nausea"],
        "urgent_if": ["radiating to arm", "with shortness of breath", "severe"],
        "recommendation": "Seek immediate medical attention if severe or accompanied by other symptoms"
    },
    "headache": {
        "category": SymptomCategory.NEUROLOGICAL,
        "risk_level": RiskLevel.MODERATE,
        "associated": ["nausea", "sensitivity_to_light", "neck_stiffness"],
        "urgent_if": ["sudden onset", "worst ever", "with fever and neck stiffness"],
        "recommendation": "Monitor and seek care if persistent or severe"
    },
    "shortness_of_breath": {
        "category": SymptomCategory.RESPIRATORY,
        "risk_level": RiskLevel.HIGH,
        "associated": ["chest_pain", "cough", "wheezing"],
        "urgent_if": ["sudden onset", "at rest", "with chest pain"],
        "recommendation": "Seek medical attention, especially if sudden or severe"
    },
    "fatigue": {
        "category": SymptomCategory.GENERAL,
        "risk_level": RiskLevel.LOW,
        "associated": ["weakness", "difficulty_concentrating", "sleep_problems"],
        "urgent_if": ["severe and sudden", "with other concerning symptoms"],
        "recommendation": "Rest and monitor, see doctor if persistent"
    },
    "dizziness": {
        "category": SymptomCategory.NEUROLOGICAL,
        "risk_level": RiskLevel.MODERATE,
        "associated": ["nausea", "headache", "vision_changes"],
        "urgent_if": ["with chest pain", "with severe headache", "loss of consciousness"],
        "recommendation": "Sit or lie down, seek care if severe or recurring"
    },
    "nausea": {
        "category": SymptomCategory.GASTROINTESTINAL,
        "risk_level": RiskLevel.LOW,
        "associated": ["vomiting", "abdominal_pain", "diarrhea"],
        "urgent_if": ["blood in vomit", "severe abdominal pain", "dehydration"],
        "recommendation": "Stay hydrated, seek care if persistent or severe"
    },
    "fever": {
        "category": SymptomCategory.GENERAL,
        "risk_level": RiskLevel.MODERATE,
        "associated": ["chills", "sweating", "body_aches"],
        "urgent_if": ["very high (>103F/39.4C)", "with neck stiffness", "with rash"],
        "recommendation": "Rest, stay hydrated, seek care if high or persistent"
    },
}


class SymptomAnalysisAgent(BaseAgent):
    """
    Agent responsible for symptom tracking and analysis.

    Capabilities:
    - Symptom recording and tracking
    - Pattern detection
    - Risk assessment
    - Correlation with other health data
    - Recommendations
    """

    def __init__(self, agent_id: str | None = None):
        super().__init__(
            agent_id=agent_id,
            name="SymptomAnalysisAgent",
            description="Analyzes patient symptoms and detects patterns",
            capabilities=[
                AgentCapability.SYMPTOM_ANALYSIS,
                AgentCapability.DATA_ANALYSIS,
                AgentCapability.RECOMMENDATION,
            ]
        )

        # Symptom history (patient_id -> list of reports)
        self._symptom_history: dict[str, list[SymptomReport]] = {}

        # Detected patterns (patient_id -> list of patterns)
        self._patterns: dict[str, list[SymptomPattern]] = {}

        # Subscribe to events
        self.subscribe_to_event(EventType.SYMPTOM_REPORTED)
        self.subscribe_to_event(EventType.VITAL_ANOMALY)

    async def on_start(self) -> None:
        """Initialize agent."""
        logger.info(f"{self.name} started - analyzing symptoms")

    async def handle_message(self, message: Message) -> Message | None:
        """Handle incoming messages."""
        content = message.content
        action = content.get("action")

        handlers = {
            "report_symptom": self._handle_report_symptom,
            "get_symptoms": self._handle_get_symptoms,
            "analyze_symptoms": self._handle_analyze_symptoms,
            "get_patterns": self._handle_get_patterns,
            "resolve_symptom": self._handle_resolve_symptom,
            "get_risk_assessment": self._handle_get_risk_assessment,
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
        if event.event_type == EventType.SYMPTOM_REPORTED:
            await self._process_symptom_event(event)
        elif event.event_type == EventType.VITAL_ANOMALY:
            await self._correlate_with_vitals(event)

    async def report_symptom(
        self,
        patient_id: str,
        symptom_name: str,
        severity: SymptomSeverity,
        description: str = "",
        location: str | None = None,
        onset_time: datetime | None = None,
        duration_hours: float | None = None,
        triggers: list[str] | None = None,
        relieving_factors: list[str] | None = None,
        associated_symptoms: list[str] | None = None,
        notes: str = ""
    ) -> dict[str, Any]:
        """
        Report a new symptom.

        Returns:
            Analysis result including risk assessment and recommendations
        """
        # Determine category
        symptom_lower = symptom_name.lower().replace(" ", "_")
        symptom_info = SYMPTOM_CORRELATIONS.get(symptom_lower, {})
        category = symptom_info.get("category", SymptomCategory.OTHER)

        report = SymptomReport(
            symptom_id=str(uuid4()),
            patient_id=patient_id,
            symptom_name=symptom_name,
            category=category,
            severity=severity,
            description=description,
            location=location,
            onset_time=onset_time or datetime.utcnow(),
            duration_hours=duration_hours,
            triggers=triggers or [],
            relieving_factors=relieving_factors or [],
            associated_symptoms=associated_symptoms or [],
            notes=notes,
        )

        # Store report
        if patient_id not in self._symptom_history:
            self._symptom_history[patient_id] = []
        self._symptom_history[patient_id].append(report)

        # Update health context
        context = self.get_health_context(patient_id)
        if context:
            context.add_symptom({
                "symptom_id": report.symptom_id,
                "name": symptom_name,
                "severity": severity.value,
                "reported_at": report.reported_at.isoformat(),
            })

        # Analyze the symptom
        analysis = await self._analyze_symptom(report)

        # Detect patterns
        patterns = self._detect_patterns(patient_id)

        # Publish event
        await self._publish_event(
            EventType.SYMPTOM_REPORTED,
            {
                "symptom_id": report.symptom_id,
                "symptom_name": symptom_name,
                "severity": severity.value,
                "category": category.value,
                "analysis": analysis,
            },
            patient_id=patient_id,
            tags=[symptom_lower, category.value, f"severity_{severity.value}"]
        )

        # Check for escalation
        if analysis["risk_level"] in ["high", "critical"]:
            await self._publish_event(
                EventType.SYMPTOM_ESCALATION,
                {
                    "symptom_id": report.symptom_id,
                    "symptom_name": symptom_name,
                    "severity": severity.value,
                    "risk_level": analysis["risk_level"],
                    "recommendation": analysis["recommendation"],
                },
                patient_id=patient_id,
                tags=["escalation", analysis["risk_level"]]
            )

        return {
            "symptom_id": report.symptom_id,
            "analysis": analysis,
            "patterns_detected": len(patterns),
            "active_symptoms": len(self._get_active_symptoms(patient_id)),
        }

    async def _analyze_symptom(self, report: SymptomReport) -> dict[str, Any]:
        """Analyze a symptom report."""
        symptom_lower = report.symptom_name.lower().replace(" ", "_")
        symptom_info = SYMPTOM_CORRELATIONS.get(symptom_lower, {})

        # Determine base risk level
        base_risk = symptom_info.get("risk_level", RiskLevel.LOW)

        # Adjust risk based on severity
        if report.severity == SymptomSeverity.CRITICAL:
            risk_level = RiskLevel.CRITICAL
        elif report.severity == SymptomSeverity.SEVERE:
            risk_level = RiskLevel.HIGH if base_risk != RiskLevel.CRITICAL else RiskLevel.CRITICAL
        else:
            risk_level = base_risk

        # Check for urgent conditions
        urgent_conditions = symptom_info.get("urgent_if", [])
        urgency_matched = []
        description_lower = report.description.lower()

        for condition in urgent_conditions:
            if condition.lower() in description_lower:
                urgency_matched.append(condition)
                risk_level = RiskLevel.HIGH if risk_level.value < RiskLevel.HIGH.value else risk_level

        # Check for associated symptoms
        known_associated = symptom_info.get("associated", [])
        matching_associated = [
            s for s in report.associated_symptoms
            if s.lower().replace(" ", "_") in known_associated
        ]

        # Get recommendation
        recommendation = symptom_info.get(
            "recommendation",
            "Monitor your symptoms and consult a healthcare provider if they persist or worsen."
        )

        # Update context risk level
        context = self.get_health_context(report.patient_id)
        if context:
            context.update_risk_level(f"symptom_{symptom_lower}", risk_level)

        return {
            "risk_level": risk_level.value,
            "category": report.category.value,
            "urgency_flags": urgency_matched,
            "associated_symptoms_detected": matching_associated,
            "expected_associated": known_associated,
            "recommendation": recommendation,
            "requires_attention": risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL],
        }

    def _detect_patterns(self, patient_id: str) -> list[SymptomPattern]:
        """Detect patterns in symptom history."""
        if patient_id not in self._symptom_history:
            return []

        history = self._symptom_history[patient_id]
        recent = [r for r in history if r.reported_at > datetime.utcnow() - timedelta(days=30)]

        if len(recent) < 3:
            return []

        new_patterns = []

        # Pattern 1: Recurring symptoms
        symptom_counts: dict[str, int] = {}
        for report in recent:
            key = report.symptom_name.lower()
            symptom_counts[key] = symptom_counts.get(key, 0) + 1

        for symptom, count in symptom_counts.items():
            if count >= 3:
                pattern = SymptomPattern(
                    pattern_id=str(uuid4()),
                    patient_id=patient_id,
                    pattern_type="recurring",
                    symptoms=[symptom],
                    frequency=f"{count} times in 30 days",
                    confidence=min(0.9, 0.5 + (count * 0.1)),
                    description=f"Recurring {symptom} detected",
                    recommendation=f"Consider discussing recurring {symptom} with your healthcare provider",
                )
                new_patterns.append(pattern)

        # Pattern 2: Symptom clusters
        # Group symptoms by day
        symptoms_by_day: dict[str, list[str]] = {}
        for report in recent:
            day_key = report.reported_at.date().isoformat()
            if day_key not in symptoms_by_day:
                symptoms_by_day[day_key] = []
            symptoms_by_day[day_key].append(report.symptom_name.lower())

        # Find co-occurring symptoms
        co_occurrences: dict[tuple[str, str], int] = {}
        for day_symptoms in symptoms_by_day.values():
            if len(day_symptoms) >= 2:
                unique = list(set(day_symptoms))
                for i in range(len(unique)):
                    for j in range(i + 1, len(unique)):
                        pair = tuple(sorted([unique[i], unique[j]]))
                        co_occurrences[pair] = co_occurrences.get(pair, 0) + 1

        for pair, count in co_occurrences.items():
            if count >= 2:
                pattern = SymptomPattern(
                    pattern_id=str(uuid4()),
                    patient_id=patient_id,
                    pattern_type="cluster",
                    symptoms=list(pair),
                    frequency=f"{count} co-occurrences in 30 days",
                    confidence=min(0.85, 0.4 + (count * 0.15)),
                    description=f"{pair[0]} and {pair[1]} often occur together",
                    recommendation="These symptoms may be related; discuss with your healthcare provider",
                )
                new_patterns.append(pattern)

        # Store patterns
        if patient_id not in self._patterns:
            self._patterns[patient_id] = []
        self._patterns[patient_id].extend(new_patterns)

        # Publish pattern event if significant patterns found
        if new_patterns:
            # Would normally await this in an async context
            pass

        return new_patterns

    def _get_active_symptoms(self, patient_id: str) -> list[SymptomReport]:
        """Get currently active symptoms for a patient."""
        if patient_id not in self._symptom_history:
            return []

        # Consider symptoms active if reported in last 48 hours and not resolved
        cutoff = datetime.utcnow() - timedelta(hours=48)

        return [
            r for r in self._symptom_history[patient_id]
            if r.reported_at > cutoff and r.resolved_at is None
        ]

    def get_risk_assessment(self, patient_id: str) -> dict[str, Any]:
        """Get comprehensive risk assessment based on symptoms."""
        active = self._get_active_symptoms(patient_id)

        if not active:
            return {
                "overall_risk": RiskLevel.LOW.value,
                "active_symptoms": 0,
                "concerns": [],
                "recommendations": [],
            }

        # Calculate overall risk
        max_severity = max(s.severity.value for s in active)
        concerns = []
        recommendations = set()

        for symptom in active:
            symptom_lower = symptom.symptom_name.lower().replace(" ", "_")
            symptom_info = SYMPTOM_CORRELATIONS.get(symptom_lower, {})

            if symptom.severity in [SymptomSeverity.SEVERE, SymptomSeverity.CRITICAL]:
                concerns.append(f"Severe {symptom.symptom_name}")

            rec = symptom_info.get("recommendation")
            if rec:
                recommendations.add(rec)

        # Determine overall risk level
        if max_severity >= SymptomSeverity.CRITICAL.value:
            overall_risk = RiskLevel.CRITICAL
        elif max_severity >= SymptomSeverity.SEVERE.value:
            overall_risk = RiskLevel.HIGH
        elif max_severity >= SymptomSeverity.MODERATE.value:
            overall_risk = RiskLevel.MODERATE
        else:
            overall_risk = RiskLevel.LOW

        # Escalate if multiple symptoms
        if len(active) >= 3 and overall_risk == RiskLevel.LOW:
            overall_risk = RiskLevel.MODERATE

        return {
            "overall_risk": overall_risk.value,
            "active_symptoms": len(active),
            "symptoms": [
                {
                    "name": s.symptom_name,
                    "severity": s.severity.value,
                    "duration_hours": s.duration_hours,
                }
                for s in active
            ],
            "concerns": concerns,
            "recommendations": list(recommendations),
        }

    async def _correlate_with_vitals(self, event: Event) -> None:
        """Correlate symptoms with vital sign anomalies."""
        patient_id = event.patient_id
        if not patient_id:
            return

        # Check if patient has related symptoms
        active = self._get_active_symptoms(patient_id)

        vital_type = event.data.get("vital_type", "")

        # Simple correlation rules
        correlations = {
            "heart_rate": ["chest_pain", "shortness_of_breath", "dizziness"],
            "blood_pressure": ["headache", "dizziness", "chest_pain"],
            "oxygen_saturation": ["shortness_of_breath", "fatigue"],
            "temperature": ["fever", "chills", "fatigue"],
        }

        related_symptoms = correlations.get(vital_type, [])
        found_correlations = []

        for symptom in active:
            symptom_lower = symptom.symptom_name.lower().replace(" ", "_")
            if symptom_lower in related_symptoms:
                found_correlations.append(symptom.symptom_name)

        if found_correlations:
            # Add insight to context
            context = self.get_health_context(patient_id)
            if context:
                context.add_insight({
                    "type": "vital_symptom_correlation",
                    "vital": vital_type,
                    "symptoms": found_correlations,
                    "timestamp": datetime.utcnow().isoformat(),
                    "message": f"Abnormal {vital_type} may be related to: {', '.join(found_correlations)}"
                })

    async def _handle_report_symptom(self, message: Message) -> Message:
        """Handle report symptom request."""
        content = message.content
        try:
            result = await self.report_symptom(
                patient_id=content["patient_id"],
                symptom_name=content["symptom_name"],
                severity=SymptomSeverity(content["severity"]),
                description=content.get("description", ""),
                location=content.get("location"),
                onset_time=datetime.fromisoformat(content["onset_time"]) if content.get("onset_time") else None,
                duration_hours=content.get("duration_hours"),
                triggers=content.get("triggers"),
                relieving_factors=content.get("relieving_factors"),
                associated_symptoms=content.get("associated_symptoms"),
                notes=content.get("notes", ""),
            )
            return message.create_response(self.agent_id, {"success": True, **result})
        except Exception as e:
            return message.create_response(self.agent_id, {"success": False, "error": str(e)})

    async def _handle_get_symptoms(self, message: Message) -> Message:
        """Handle get symptoms request."""
        content = message.content
        patient_id = content.get("patient_id")
        active_only = content.get("active_only", True)
        limit = content.get("limit", 50)

        if patient_id not in self._symptom_history:
            return message.create_response(
                self.agent_id,
                {"success": True, "symptoms": []}
            )

        if active_only:
            symptoms = self._get_active_symptoms(patient_id)
        else:
            symptoms = self._symptom_history[patient_id][-limit:]

        return message.create_response(
            self.agent_id,
            {
                "success": True,
                "symptoms": [
                    {
                        "symptom_id": s.symptom_id,
                        "name": s.symptom_name,
                        "category": s.category.value,
                        "severity": s.severity.value,
                        "reported_at": s.reported_at.isoformat(),
                        "resolved_at": s.resolved_at.isoformat() if s.resolved_at else None,
                    }
                    for s in symptoms
                ],
            }
        )

    async def _handle_analyze_symptoms(self, message: Message) -> Message:
        """Handle analyze symptoms request."""
        patient_id = message.content.get("patient_id")
        assessment = self.get_risk_assessment(patient_id)

        # Get patterns
        patterns = self._patterns.get(patient_id, [])[-10:]

        return message.create_response(
            self.agent_id,
            {
                "success": True,
                "assessment": assessment,
                "patterns": [
                    {
                        "type": p.pattern_type,
                        "symptoms": p.symptoms,
                        "frequency": p.frequency,
                        "confidence": p.confidence,
                        "description": p.description,
                    }
                    for p in patterns
                ],
            }
        )

    async def _handle_get_patterns(self, message: Message) -> Message:
        """Handle get patterns request."""
        patient_id = message.content.get("patient_id")
        patterns = self._patterns.get(patient_id, [])

        return message.create_response(
            self.agent_id,
            {
                "success": True,
                "patterns": [
                    {
                        "pattern_id": p.pattern_id,
                        "type": p.pattern_type,
                        "symptoms": p.symptoms,
                        "frequency": p.frequency,
                        "confidence": p.confidence,
                        "description": p.description,
                        "recommendation": p.recommendation,
                    }
                    for p in patterns
                ],
            }
        )

    async def _handle_resolve_symptom(self, message: Message) -> Message:
        """Handle resolve symptom request."""
        content = message.content
        patient_id = content.get("patient_id")
        symptom_id = content.get("symptom_id")

        if patient_id not in self._symptom_history:
            return message.create_response(
                self.agent_id,
                {"success": False, "error": "Patient not found"}
            )

        for symptom in self._symptom_history[patient_id]:
            if symptom.symptom_id == symptom_id:
                symptom.resolved_at = datetime.utcnow()
                return message.create_response(
                    self.agent_id,
                    {"success": True, "message": "Symptom marked as resolved"}
                )

        return message.create_response(
            self.agent_id,
            {"success": False, "error": "Symptom not found"}
        )

    async def _handle_get_risk_assessment(self, message: Message) -> Message:
        """Handle get risk assessment request."""
        patient_id = message.content.get("patient_id")
        assessment = self.get_risk_assessment(patient_id)

        return message.create_response(
            self.agent_id,
            {"success": True, **assessment}
        )

    async def _process_symptom_event(self, event: Event) -> None:
        """Process incoming symptom event."""
        # Could trigger additional analysis or pattern detection
        logger.debug(f"Symptom event processed for patient {event.patient_id}")
