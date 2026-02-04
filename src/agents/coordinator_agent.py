"""Coordinator agent for orchestrating health monitoring agents."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from ..core.base_agent import AgentCapability, BaseAgent
from ..core.context import HealthContext, RiskLevel
from ..core.event_bus import Event, EventType
from ..core.message import Message, MessageType

logger = logging.getLogger(__name__)


@dataclass
class HealthSummary:
    """Comprehensive health summary for a patient."""

    patient_id: str
    generated_at: datetime
    overall_status: str
    risk_level: RiskLevel
    vitals_status: dict[str, Any]
    medication_adherence: float
    active_symptoms: int
    active_alerts: int
    wellness_score: float
    insights: list[dict[str, Any]]
    recommendations: list[dict[str, Any]]
    action_items: list[dict[str, Any]]


@dataclass
class CareTask:
    """A coordinated care task."""

    task_id: str
    patient_id: str
    task_type: str
    description: str
    assigned_agents: list[str]
    status: str = "pending"  # pending, in_progress, completed, failed
    priority: int = 1
    due_at: datetime | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    result: dict[str, Any] = field(default_factory=dict)


class CoordinatorAgent(BaseAgent):
    """
    Central coordinator agent for the health monitoring system.

    Responsibilities:
    - Orchestrating other agents
    - Generating comprehensive health summaries
    - Coordinating care tasks
    - Managing cross-agent insights
    - Providing unified health assessments
    """

    def __init__(self, agent_id: str | None = None):
        super().__init__(
            agent_id=agent_id,
            name="CoordinatorAgent",
            description="Orchestrates health monitoring agents and provides unified insights",
            capabilities=[
                AgentCapability.COORDINATION,
                AgentCapability.DATA_ANALYSIS,
                AgentCapability.RECOMMENDATION,
            ]
        )

        # Care tasks (task_id -> task)
        self._care_tasks: dict[str, CareTask] = {}

        # Patient care tasks (patient_id -> list of task_ids)
        self._patient_tasks: dict[str, list[str]] = {}

        # Health summaries cache (patient_id -> summary)
        self._summaries: dict[str, HealthSummary] = {}

        # Insights collected from all agents (patient_id -> insights)
        self._collected_insights: dict[str, list[dict[str, Any]]] = {}

        # Subscribe to all major events for coordination
        self.subscribe_to_event(EventType.VITAL_ANOMALY)
        self.subscribe_to_event(EventType.SYMPTOM_ESCALATION)
        self.subscribe_to_event(EventType.MEDICATION_MISSED)
        self.subscribe_to_event(EventType.HEALTH_ALERT)
        self.subscribe_to_event(EventType.HEALTH_INSIGHT)
        self.subscribe_to_event(EventType.RISK_ASSESSMENT)

    async def on_start(self) -> None:
        """Initialize coordinator."""
        logger.info(f"{self.name} started - coordinating health monitoring")

    async def handle_message(self, message: Message) -> Message | None:
        """Handle incoming messages."""
        content = message.content
        action = content.get("action")

        handlers = {
            "get_health_summary": self._handle_get_health_summary,
            "get_dashboard_data": self._handle_get_dashboard_data,
            "create_care_task": self._handle_create_care_task,
            "get_care_tasks": self._handle_get_care_tasks,
            "complete_task": self._handle_complete_task,
            "get_insights": self._handle_get_insights,
            "get_risk_assessment": self._handle_get_risk_assessment,
            "get_recommendations": self._handle_get_recommendations,
        }

        handler = handlers.get(action)
        if handler:
            return await handler(message)

        return message.create_response(
            self.agent_id,
            {"error": f"Unknown action: {action}"}
        )

    async def handle_event(self, event: Event) -> None:
        """Handle events for coordination."""
        patient_id = event.patient_id

        if event.event_type == EventType.HEALTH_INSIGHT:
            await self._collect_insight(patient_id, event.data)
        elif event.event_type == EventType.VITAL_ANOMALY:
            await self._handle_vital_anomaly_coordination(event)
        elif event.event_type == EventType.SYMPTOM_ESCALATION:
            await self._handle_symptom_coordination(event)

    async def generate_health_summary(self, patient_id: str) -> HealthSummary:
        """
        Generate comprehensive health summary for a patient.

        Aggregates data from all agents to provide a unified view.
        """
        context = self.get_health_context(patient_id)
        if not context:
            raise ValueError(f"No health context for patient {patient_id}")

        # Analyze current state
        vitals_status = self._analyze_vitals_status(context)
        overall_risk = self._calculate_overall_risk(context)
        wellness_score = self._calculate_wellness_score(context)

        # Gather insights
        insights = self._collected_insights.get(patient_id, [])[-10:]

        # Generate recommendations
        recommendations = self._generate_recommendations(context, overall_risk)

        # Create action items
        action_items = self._create_action_items(context)

        # Determine overall status
        if overall_risk == RiskLevel.CRITICAL:
            overall_status = "requires_immediate_attention"
        elif overall_risk == RiskLevel.HIGH:
            overall_status = "needs_attention"
        elif overall_risk == RiskLevel.MODERATE:
            overall_status = "stable_with_concerns"
        else:
            overall_status = "healthy"

        summary = HealthSummary(
            patient_id=patient_id,
            generated_at=datetime.utcnow(),
            overall_status=overall_status,
            risk_level=overall_risk,
            vitals_status=vitals_status,
            medication_adherence=self._get_medication_adherence(context),
            active_symptoms=len(context.active_symptoms),
            active_alerts=len(context.active_alerts),
            wellness_score=wellness_score,
            insights=insights,
            recommendations=recommendations,
            action_items=action_items,
        )

        self._summaries[patient_id] = summary

        return summary

    def _analyze_vitals_status(self, context: HealthContext) -> dict[str, Any]:
        """Analyze vital signs status."""
        vitals = context.current_vitals
        status = {
            "all_normal": True,
            "concerns": [],
            "latest_readings": {},
        }

        for vital_type, data in vitals.items():
            status["latest_readings"][vital_type] = data.get("value")

            # Check if there are any risk levels associated
            risk_key = f"vital_{vital_type}"
            if risk_key in context.risk_levels:
                risk = context.risk_levels[risk_key]
                if risk != RiskLevel.LOW:
                    status["all_normal"] = False
                    status["concerns"].append({
                        "vital": vital_type,
                        "risk_level": risk.value,
                    })

        return status

    def _calculate_overall_risk(self, context: HealthContext) -> RiskLevel:
        """Calculate overall risk level from all factors."""
        if not context.risk_levels:
            return RiskLevel.LOW

        # Get maximum risk level
        max_risk = max(
            (r.value for r in context.risk_levels.values()),
            default=RiskLevel.LOW.value
        )

        # Factor in number of concerns
        num_high_risks = sum(
            1 for r in context.risk_levels.values()
            if r.value >= RiskLevel.HIGH.value
        )

        # Escalate if multiple high-risk factors
        if num_high_risks >= 2 and max_risk < RiskLevel.CRITICAL.value:
            max_risk = min(max_risk + 1, RiskLevel.CRITICAL.value)

        # Factor in active alerts
        if len(context.active_alerts) >= 3:
            max_risk = min(max_risk + 1, RiskLevel.CRITICAL.value)

        return RiskLevel(max_risk)

    def _calculate_wellness_score(self, context: HealthContext) -> float:
        """Calculate wellness score (0-100)."""
        score = 100.0

        # Deduct for risk levels
        for risk in context.risk_levels.values():
            if risk == RiskLevel.MODERATE:
                score -= 5
            elif risk == RiskLevel.HIGH:
                score -= 15
            elif risk == RiskLevel.CRITICAL:
                score -= 30

        # Deduct for active symptoms
        score -= len(context.active_symptoms) * 5

        # Deduct for active alerts
        score -= len(context.active_alerts) * 3

        # Factor in wellness data if available
        wellness = context.wellness_data
        if wellness.get("mood"):
            mood = wellness["mood"]
            if mood.get("level") == "LOW":
                score -= 10
            elif mood.get("level") == "VERY_LOW":
                score -= 20

        return max(0, min(100, score))

    def _get_medication_adherence(self, context: HealthContext) -> float:
        """Get medication adherence rate."""
        # This would normally query the medication agent
        # For now, return a default
        return 85.0

    def _generate_recommendations(
        self,
        context: HealthContext,
        risk_level: RiskLevel
    ) -> list[dict[str, Any]]:
        """Generate personalized recommendations."""
        recommendations = []

        if risk_level == RiskLevel.CRITICAL:
            recommendations.append({
                "priority": "critical",
                "category": "medical",
                "recommendation": "Seek immediate medical attention",
                "reason": "Multiple critical health indicators detected",
            })

        if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]:
            recommendations.append({
                "priority": "high",
                "category": "medical",
                "recommendation": "Contact your healthcare provider today",
                "reason": "Health indicators require professional review",
            })

        # Check for specific issues
        for risk_key, risk_value in context.risk_levels.items():
            if "vital_heart_rate" in risk_key and risk_value != RiskLevel.LOW:
                recommendations.append({
                    "priority": "medium",
                    "category": "lifestyle",
                    "recommendation": "Monitor your heart rate and avoid strenuous activity",
                    "reason": "Abnormal heart rate patterns detected",
                })

        if len(context.active_symptoms) > 0:
            recommendations.append({
                "priority": "medium",
                "category": "monitoring",
                "recommendation": "Continue tracking your symptoms and note any changes",
                "reason": f"{len(context.active_symptoms)} active symptom(s)",
            })

        if not recommendations:
            recommendations.append({
                "priority": "low",
                "category": "wellness",
                "recommendation": "Continue maintaining your healthy lifestyle",
                "reason": "All health indicators are within normal ranges",
            })

        return recommendations

    def _create_action_items(self, context: HealthContext) -> list[dict[str, Any]]:
        """Create actionable items for the patient."""
        items = []

        # Check alerts
        for alert in context.active_alerts:
            items.append({
                "type": "alert",
                "title": f"Review alert: {alert.get('title', 'Health Alert')}",
                "urgency": alert.get("severity", "normal"),
            })

        # Add medication reminders if needed
        # This would normally check the medication schedule

        # Add wellness suggestions based on data gaps
        wellness = context.wellness_data
        if not wellness.get("last_activity"):
            items.append({
                "type": "wellness",
                "title": "Log your physical activity",
                "urgency": "low",
            })

        if not wellness.get("last_sleep"):
            items.append({
                "type": "wellness",
                "title": "Log your sleep data",
                "urgency": "low",
            })

        return items

    async def _collect_insight(
        self,
        patient_id: str | None,
        insight: dict[str, Any]
    ) -> None:
        """Collect insight from an agent."""
        if not patient_id:
            return

        if patient_id not in self._collected_insights:
            self._collected_insights[patient_id] = []

        insight["collected_at"] = datetime.utcnow().isoformat()
        self._collected_insights[patient_id].append(insight)

        # Keep last 100 insights
        if len(self._collected_insights[patient_id]) > 100:
            self._collected_insights[patient_id] = \
                self._collected_insights[patient_id][-100:]

    async def _handle_vital_anomaly_coordination(self, event: Event) -> None:
        """Coordinate response to vital anomaly."""
        patient_id = event.patient_id
        if not patient_id:
            return

        data = event.data
        risk_level = data.get("risk_level", "moderate")

        # Create a care task for high-risk anomalies
        if risk_level in ["high", "critical"]:
            await self.create_care_task(
                patient_id=patient_id,
                task_type="vital_review",
                description=f"Review abnormal {data.get('vital_type', 'vital')} reading",
                assigned_agents=["VitalSignsAgent", "AlertAgent"],
                priority=3 if risk_level == "critical" else 2,
            )

    async def _handle_symptom_coordination(self, event: Event) -> None:
        """Coordinate response to symptom escalation."""
        patient_id = event.patient_id
        if not patient_id:
            return

        data = event.data
        symptom_name = data.get("symptom_name", "unknown")
        risk_level = data.get("risk_level", "moderate")

        # Create insight
        insight = {
            "type": "symptom_correlation",
            "symptom": symptom_name,
            "risk_level": risk_level,
            "message": f"Symptom escalation detected: {symptom_name}",
            "source": "SymptomAnalysisAgent",
        }

        await self._collect_insight(patient_id, insight)

    async def create_care_task(
        self,
        patient_id: str,
        task_type: str,
        description: str,
        assigned_agents: list[str],
        priority: int = 1,
        due_hours: float | None = None
    ) -> CareTask:
        """Create a coordinated care task."""
        task = CareTask(
            task_id=str(uuid4()),
            patient_id=patient_id,
            task_type=task_type,
            description=description,
            assigned_agents=assigned_agents,
            priority=priority,
            due_at=datetime.utcnow() + timedelta(hours=due_hours) if due_hours else None,
        )

        self._care_tasks[task.task_id] = task

        if patient_id not in self._patient_tasks:
            self._patient_tasks[patient_id] = []
        self._patient_tasks[patient_id].append(task.task_id)

        logger.info(f"Created care task {task.task_id} for patient {patient_id}")

        return task

    def get_dashboard_data(self, patient_id: str) -> dict[str, Any]:
        """Get data for the patient dashboard."""
        context = self.get_health_context(patient_id)
        if not context:
            return {"error": "Patient not found"}

        # Get or generate summary
        summary = self._summaries.get(patient_id)

        return {
            "patient": {
                "id": patient_id,
                "name": f"{context.profile.first_name} {context.profile.last_name}",
                "age": context.profile.age,
            },
            "overview": {
                "overall_status": summary.overall_status if summary else "unknown",
                "risk_level": summary.risk_level.value if summary else "low",
                "wellness_score": summary.wellness_score if summary else 0,
            },
            "vitals": context.current_vitals,
            "active_symptoms": len(context.active_symptoms),
            "active_alerts": len(context.active_alerts),
            "recent_insights": context.insights[-5:],
            "recommendations": context.recommendations[-3:],
            "wellness": context.wellness_data,
            "last_updated": context.last_updated.isoformat(),
        }

    # Message handlers

    async def _handle_get_health_summary(self, message: Message) -> Message:
        """Handle get health summary request."""
        patient_id = message.content.get("patient_id")
        try:
            summary = await self.generate_health_summary(patient_id)
            return message.create_response(
                self.agent_id,
                {
                    "success": True,
                    "summary": {
                        "overall_status": summary.overall_status,
                        "risk_level": summary.risk_level.value,
                        "vitals_status": summary.vitals_status,
                        "medication_adherence": summary.medication_adherence,
                        "active_symptoms": summary.active_symptoms,
                        "active_alerts": summary.active_alerts,
                        "wellness_score": summary.wellness_score,
                        "insights": summary.insights,
                        "recommendations": summary.recommendations,
                        "action_items": summary.action_items,
                        "generated_at": summary.generated_at.isoformat(),
                    },
                }
            )
        except Exception as e:
            return message.create_response(
                self.agent_id,
                {"success": False, "error": str(e)}
            )

    async def _handle_get_dashboard_data(self, message: Message) -> Message:
        """Handle get dashboard data request."""
        patient_id = message.content.get("patient_id")
        data = self.get_dashboard_data(patient_id)
        return message.create_response(
            self.agent_id,
            {"success": True, **data}
        )

    async def _handle_create_care_task(self, message: Message) -> Message:
        """Handle create care task request."""
        content = message.content
        try:
            task = await self.create_care_task(
                patient_id=content["patient_id"],
                task_type=content["task_type"],
                description=content["description"],
                assigned_agents=content.get("assigned_agents", []),
                priority=content.get("priority", 1),
                due_hours=content.get("due_hours"),
            )
            return message.create_response(
                self.agent_id,
                {
                    "success": True,
                    "task_id": task.task_id,
                }
            )
        except Exception as e:
            return message.create_response(
                self.agent_id,
                {"success": False, "error": str(e)}
            )

    async def _handle_get_care_tasks(self, message: Message) -> Message:
        """Handle get care tasks request."""
        patient_id = message.content.get("patient_id")
        task_ids = self._patient_tasks.get(patient_id, [])

        tasks = []
        for task_id in task_ids:
            task = self._care_tasks.get(task_id)
            if task:
                tasks.append({
                    "task_id": task.task_id,
                    "type": task.task_type,
                    "description": task.description,
                    "status": task.status,
                    "priority": task.priority,
                    "created_at": task.created_at.isoformat(),
                    "due_at": task.due_at.isoformat() if task.due_at else None,
                })

        return message.create_response(
            self.agent_id,
            {"success": True, "tasks": tasks}
        )

    async def _handle_complete_task(self, message: Message) -> Message:
        """Handle complete task request."""
        content = message.content
        task_id = content.get("task_id")

        if task_id in self._care_tasks:
            task = self._care_tasks[task_id]
            task.status = "completed"
            task.completed_at = datetime.utcnow()
            task.result = content.get("result", {})
            return message.create_response(
                self.agent_id,
                {"success": True}
            )

        return message.create_response(
            self.agent_id,
            {"success": False, "error": "Task not found"}
        )

    async def _handle_get_insights(self, message: Message) -> Message:
        """Handle get insights request."""
        patient_id = message.content.get("patient_id")
        limit = message.content.get("limit", 20)

        insights = self._collected_insights.get(patient_id, [])[-limit:]

        return message.create_response(
            self.agent_id,
            {"success": True, "insights": insights}
        )

    async def _handle_get_risk_assessment(self, message: Message) -> Message:
        """Handle get risk assessment request."""
        patient_id = message.content.get("patient_id")
        context = self.get_health_context(patient_id)

        if not context:
            return message.create_response(
                self.agent_id,
                {"success": False, "error": "Patient not found"}
            )

        overall_risk = self._calculate_overall_risk(context)

        return message.create_response(
            self.agent_id,
            {
                "success": True,
                "overall_risk": overall_risk.value,
                "risk_factors": {
                    k: v.value for k, v in context.risk_levels.items()
                },
                "active_alerts": len(context.active_alerts),
                "active_symptoms": len(context.active_symptoms),
            }
        )

    async def _handle_get_recommendations(self, message: Message) -> Message:
        """Handle get recommendations request."""
        patient_id = message.content.get("patient_id")
        context = self.get_health_context(patient_id)

        if not context:
            return message.create_response(
                self.agent_id,
                {"success": False, "error": "Patient not found"}
            )

        overall_risk = self._calculate_overall_risk(context)
        recommendations = self._generate_recommendations(context, overall_risk)

        return message.create_response(
            self.agent_id,
            {"success": True, "recommendations": recommendations}
        )
