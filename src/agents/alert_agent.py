"""Alert management agent."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

from ..core.base_agent import AgentCapability, BaseAgent
from ..core.context import RiskLevel
from ..core.event_bus import Event, EventType
from ..core.message import Message, MessagePriority

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""

    INFO = 1
    WARNING = 2
    URGENT = 3
    CRITICAL = 4
    EMERGENCY = 5


class AlertCategory(Enum):
    """Categories of alerts."""

    VITAL_SIGNS = "vital_signs"
    MEDICATION = "medication"
    SYMPTOM = "symptom"
    WELLNESS = "wellness"
    APPOINTMENT = "appointment"
    SYSTEM = "system"
    EMERGENCY = "emergency"


class AlertStatus(Enum):
    """Alert status."""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    EXPIRED = "expired"


@dataclass
class Alert:
    """Health alert."""

    alert_id: str
    patient_id: str
    category: AlertCategory
    severity: AlertSeverity
    title: str
    message: str
    status: AlertStatus = AlertStatus.ACTIVE
    source_agent: str = ""
    source_event_id: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    actions: list[dict[str, str]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    expires_at: datetime | None = None
    notification_sent: bool = False
    escalation_level: int = 0


@dataclass
class NotificationChannel:
    """Notification channel configuration."""

    channel_id: str
    channel_type: str  # push, sms, email, call
    destination: str
    is_active: bool = True
    priority_threshold: AlertSeverity = AlertSeverity.WARNING


@dataclass
class EscalationRule:
    """Rule for alert escalation."""

    rule_id: str
    category: AlertCategory
    initial_severity: AlertSeverity
    escalate_after_minutes: int
    escalate_to_severity: AlertSeverity
    notify_contacts: bool = True


class AlertAgent(BaseAgent):
    """
    Agent responsible for alert management.

    Capabilities:
    - Alert generation and management
    - Notification routing
    - Alert escalation
    - Emergency response coordination
    - Alert history and analytics
    """

    def __init__(self, agent_id: str | None = None):
        super().__init__(
            agent_id=agent_id,
            name="AlertAgent",
            description="Manages health alerts, notifications, and emergency response",
            capabilities=[
                AgentCapability.ALERT_MANAGEMENT,
                AgentCapability.EMERGENCY_RESPONSE,
            ]
        )

        # Active alerts (patient_id -> alert_id -> alert)
        self._alerts: dict[str, dict[str, Alert]] = {}

        # Alert history (patient_id -> list of alerts)
        self._alert_history: dict[str, list[Alert]] = {}

        # Notification channels (patient_id -> list of channels)
        self._notification_channels: dict[str, list[NotificationChannel]] = {}

        # Escalation rules
        self._escalation_rules: list[EscalationRule] = self._create_default_rules()

        # Alert thresholds for auto-generation
        self._alert_thresholds: dict[str, dict[str, Any]] = {}

        # Subscribe to events that may trigger alerts
        self.subscribe_to_event(EventType.VITAL_ANOMALY)
        self.subscribe_to_event(EventType.SYMPTOM_ESCALATION)
        self.subscribe_to_event(EventType.MEDICATION_MISSED)
        self.subscribe_to_event(EventType.MEDICATION_INTERACTION)
        self.subscribe_to_event(EventType.HEALTH_ALERT)

    def _create_default_rules(self) -> list[EscalationRule]:
        """Create default escalation rules."""
        return [
            EscalationRule(
                rule_id="vital_critical",
                category=AlertCategory.VITAL_SIGNS,
                initial_severity=AlertSeverity.CRITICAL,
                escalate_after_minutes=5,
                escalate_to_severity=AlertSeverity.EMERGENCY,
                notify_contacts=True,
            ),
            EscalationRule(
                rule_id="vital_urgent",
                category=AlertCategory.VITAL_SIGNS,
                initial_severity=AlertSeverity.URGENT,
                escalate_after_minutes=15,
                escalate_to_severity=AlertSeverity.CRITICAL,
                notify_contacts=True,
            ),
            EscalationRule(
                rule_id="symptom_critical",
                category=AlertCategory.SYMPTOM,
                initial_severity=AlertSeverity.CRITICAL,
                escalate_after_minutes=10,
                escalate_to_severity=AlertSeverity.EMERGENCY,
                notify_contacts=True,
            ),
            EscalationRule(
                rule_id="medication_missed",
                category=AlertCategory.MEDICATION,
                initial_severity=AlertSeverity.WARNING,
                escalate_after_minutes=60,
                escalate_to_severity=AlertSeverity.URGENT,
                notify_contacts=False,
            ),
        ]

    async def on_start(self) -> None:
        """Initialize agent."""
        logger.info(f"{self.name} started - managing alerts")

    async def handle_message(self, message: Message) -> Message | None:
        """Handle incoming messages."""
        content = message.content
        action = content.get("action")

        handlers = {
            "create_alert": self._handle_create_alert,
            "acknowledge_alert": self._handle_acknowledge_alert,
            "resolve_alert": self._handle_resolve_alert,
            "get_active_alerts": self._handle_get_active_alerts,
            "get_alert_history": self._handle_get_alert_history,
            "configure_notifications": self._handle_configure_notifications,
            "trigger_emergency": self._handle_trigger_emergency,
        }

        handler = handlers.get(action)
        if handler:
            return await handler(message)

        return message.create_response(
            self.agent_id,
            {"error": f"Unknown action: {action}"}
        )

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events and generate alerts."""
        if event.event_type == EventType.VITAL_ANOMALY:
            await self._handle_vital_anomaly(event)
        elif event.event_type == EventType.SYMPTOM_ESCALATION:
            await self._handle_symptom_escalation(event)
        elif event.event_type == EventType.MEDICATION_MISSED:
            await self._handle_medication_missed(event)
        elif event.event_type == EventType.MEDICATION_INTERACTION:
            await self._handle_medication_interaction(event)

    async def create_alert(
        self,
        patient_id: str,
        category: AlertCategory,
        severity: AlertSeverity,
        title: str,
        message: str,
        source_agent: str = "",
        source_event_id: str | None = None,
        data: dict[str, Any] | None = None,
        actions: list[dict[str, str]] | None = None,
        expires_in_hours: float | None = None
    ) -> Alert:
        """
        Create a new alert.

        Args:
            patient_id: Patient identifier
            category: Alert category
            severity: Alert severity
            title: Alert title
            message: Alert message
            source_agent: Agent that triggered the alert
            source_event_id: Related event ID
            data: Additional data
            actions: Suggested actions
            expires_in_hours: Optional expiration time

        Returns:
            Created alert
        """
        alert = Alert(
            alert_id=str(uuid4()),
            patient_id=patient_id,
            category=category,
            severity=severity,
            title=title,
            message=message,
            source_agent=source_agent,
            source_event_id=source_event_id,
            data=data or {},
            actions=actions or [],
            expires_at=(
                datetime.utcnow() + timedelta(hours=expires_in_hours)
                if expires_in_hours else None
            ),
        )

        # Store alert
        if patient_id not in self._alerts:
            self._alerts[patient_id] = {}
        self._alerts[patient_id][alert.alert_id] = alert

        # Add to history
        if patient_id not in self._alert_history:
            self._alert_history[patient_id] = []
        self._alert_history[patient_id].append(alert)

        # Update health context
        context = self.get_health_context(patient_id)
        if context:
            context.add_alert({
                "id": alert.alert_id,
                "category": category.value,
                "severity": severity.value,
                "title": title,
                "created_at": alert.created_at.isoformat(),
            })

        # Send notifications
        await self._send_notifications(alert)

        # Publish event
        await self._publish_event(
            EventType.HEALTH_ALERT,
            {
                "alert_id": alert.alert_id,
                "category": category.value,
                "severity": severity.value,
                "title": title,
            },
            patient_id=patient_id,
            tags=["alert", category.value, f"severity_{severity.value}"]
        )

        logger.info(f"Created {severity.name} alert for patient {patient_id}: {title}")

        return alert

    async def acknowledge_alert(
        self,
        patient_id: str,
        alert_id: str,
        acknowledged_by: str = ""
    ) -> bool:
        """Acknowledge an alert."""
        if patient_id not in self._alerts:
            return False

        if alert_id not in self._alerts[patient_id]:
            return False

        alert = self._alerts[patient_id][alert_id]
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.utcnow()

        # Update context
        context = self.get_health_context(patient_id)
        if context:
            context.clear_alert(alert_id)

        # Publish acknowledgment
        await self._publish_event(
            EventType.ALERT_ACKNOWLEDGED,
            {
                "alert_id": alert_id,
                "acknowledged_by": acknowledged_by,
            },
            patient_id=patient_id
        )

        logger.info(f"Alert {alert_id} acknowledged for patient {patient_id}")

        return True

    async def resolve_alert(
        self,
        patient_id: str,
        alert_id: str,
        resolution_notes: str = ""
    ) -> bool:
        """Resolve an alert."""
        if patient_id not in self._alerts:
            return False

        if alert_id not in self._alerts[patient_id]:
            return False

        alert = self._alerts[patient_id][alert_id]
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow()
        alert.data["resolution_notes"] = resolution_notes

        # Remove from active alerts
        del self._alerts[patient_id][alert_id]

        # Update context
        context = self.get_health_context(patient_id)
        if context:
            context.clear_alert(alert_id)

        logger.info(f"Alert {alert_id} resolved for patient {patient_id}")

        return True

    def get_active_alerts(
        self,
        patient_id: str,
        category: AlertCategory | None = None,
        min_severity: AlertSeverity | None = None
    ) -> list[Alert]:
        """Get active alerts for a patient."""
        if patient_id not in self._alerts:
            return []

        alerts = list(self._alerts[patient_id].values())

        # Filter by category
        if category:
            alerts = [a for a in alerts if a.category == category]

        # Filter by severity
        if min_severity:
            alerts = [a for a in alerts if a.severity.value >= min_severity.value]

        # Sort by severity (highest first), then by time
        alerts.sort(key=lambda a: (-a.severity.value, a.created_at))

        return alerts

    async def trigger_emergency(
        self,
        patient_id: str,
        reason: str,
        location: str | None = None
    ) -> Alert:
        """Trigger emergency response."""
        alert = await self.create_alert(
            patient_id=patient_id,
            category=AlertCategory.EMERGENCY,
            severity=AlertSeverity.EMERGENCY,
            title="EMERGENCY ALERT",
            message=reason,
            data={
                "location": location,
                "triggered_at": datetime.utcnow().isoformat(),
            },
            actions=[
                {"action": "call_emergency", "label": "Call 911"},
                {"action": "notify_contacts", "label": "Notify Emergency Contacts"},
            ],
        )

        # Notify all emergency contacts
        await self._notify_emergency_contacts(patient_id, alert)

        logger.critical(f"EMERGENCY triggered for patient {patient_id}: {reason}")

        return alert

    async def _send_notifications(self, alert: Alert) -> None:
        """Send notifications for an alert."""
        patient_id = alert.patient_id
        channels = self._notification_channels.get(patient_id, [])

        for channel in channels:
            if not channel.is_active:
                continue

            if alert.severity.value < channel.priority_threshold.value:
                continue

            # Simulate sending notification
            await self._send_to_channel(channel, alert)

        alert.notification_sent = True

    async def _send_to_channel(
        self,
        channel: NotificationChannel,
        alert: Alert
    ) -> None:
        """Send alert to a specific channel."""
        # In a real implementation, this would integrate with
        # actual notification services (FCM, Twilio, SendGrid, etc.)
        logger.info(
            f"Sending {alert.severity.name} alert via {channel.channel_type} "
            f"to {channel.destination}: {alert.title}"
        )

    async def _notify_emergency_contacts(
        self,
        patient_id: str,
        alert: Alert
    ) -> None:
        """Notify emergency contacts."""
        context = self.get_health_context(patient_id)
        if not context:
            return

        for contact in context.profile.emergency_contacts:
            logger.info(
                f"EMERGENCY: Notifying {contact.name} ({contact.relationship}) "
                f"at {contact.phone} for patient {patient_id}"
            )
            # In real implementation, would send SMS/call

    async def _handle_vital_anomaly(self, event: Event) -> None:
        """Handle vital sign anomaly event."""
        patient_id = event.patient_id
        if not patient_id:
            return

        data = event.data
        status = data.get("status", "")
        vital_type = data.get("vital_type", "unknown")
        value = data.get("value", 0)
        risk_level = data.get("risk_level", "moderate")

        # Map risk level to severity
        severity_map = {
            "low": AlertSeverity.INFO,
            "moderate": AlertSeverity.WARNING,
            "high": AlertSeverity.URGENT,
            "critical": AlertSeverity.CRITICAL,
        }
        severity = severity_map.get(risk_level, AlertSeverity.WARNING)

        await self.create_alert(
            patient_id=patient_id,
            category=AlertCategory.VITAL_SIGNS,
            severity=severity,
            title=f"Abnormal {vital_type.replace('_', ' ').title()}",
            message=f"Your {vital_type.replace('_', ' ')} reading of {value} is {status}. Please monitor closely.",
            source_agent="VitalSignsAgent",
            source_event_id=event.event_id,
            data=data,
            actions=[
                {"action": "view_details", "label": "View Details"},
                {"action": "log_symptom", "label": "Log Related Symptoms"},
            ],
        )

    async def _handle_symptom_escalation(self, event: Event) -> None:
        """Handle symptom escalation event."""
        patient_id = event.patient_id
        if not patient_id:
            return

        data = event.data
        symptom_name = data.get("symptom_name", "unknown")
        risk_level = data.get("risk_level", "moderate")
        recommendation = data.get("recommendation", "")

        severity_map = {
            "low": AlertSeverity.INFO,
            "moderate": AlertSeverity.WARNING,
            "high": AlertSeverity.URGENT,
            "critical": AlertSeverity.CRITICAL,
        }
        severity = severity_map.get(risk_level, AlertSeverity.WARNING)

        await self.create_alert(
            patient_id=patient_id,
            category=AlertCategory.SYMPTOM,
            severity=severity,
            title=f"Symptom Alert: {symptom_name}",
            message=recommendation or f"Your reported {symptom_name} requires attention.",
            source_agent="SymptomAnalysisAgent",
            source_event_id=event.event_id,
            data=data,
            actions=[
                {"action": "view_symptoms", "label": "View Symptoms"},
                {"action": "contact_doctor", "label": "Contact Healthcare Provider"},
            ],
        )

    async def _handle_medication_missed(self, event: Event) -> None:
        """Handle missed medication event."""
        patient_id = event.patient_id
        if not patient_id:
            return

        data = event.data
        medication_id = data.get("medication_id", "")

        await self.create_alert(
            patient_id=patient_id,
            category=AlertCategory.MEDICATION,
            severity=AlertSeverity.WARNING,
            title="Missed Medication",
            message="You missed a scheduled medication dose. Please take it as soon as possible if safe to do so.",
            source_agent="MedicationAgent",
            source_event_id=event.event_id,
            data={"medication_id": medication_id},
            actions=[
                {"action": "take_now", "label": "Mark as Taken"},
                {"action": "skip", "label": "Skip This Dose"},
                {"action": "view_schedule", "label": "View Schedule"},
            ],
            expires_in_hours=4,
        )

    async def _handle_medication_interaction(self, event: Event) -> None:
        """Handle medication interaction event."""
        patient_id = event.patient_id
        if not patient_id:
            return

        data = event.data
        medication = data.get("medication", "")
        interactions = data.get("interactions", [])

        severity = AlertSeverity.WARNING
        for interaction in interactions:
            if interaction.get("severity") == "severe":
                severity = AlertSeverity.URGENT
                break

        interaction_details = "; ".join([
            f"{i['with']}: {i['description']}"
            for i in interactions
        ])

        await self.create_alert(
            patient_id=patient_id,
            category=AlertCategory.MEDICATION,
            severity=severity,
            title=f"Drug Interaction Warning: {medication}",
            message=f"Potential interactions detected: {interaction_details}",
            source_agent="MedicationAgent",
            source_event_id=event.event_id,
            data=data,
            actions=[
                {"action": "view_details", "label": "View Details"},
                {"action": "contact_pharmacist", "label": "Contact Pharmacist"},
            ],
        )

    def configure_notifications(
        self,
        patient_id: str,
        channels: list[dict[str, Any]]
    ) -> None:
        """Configure notification channels for a patient."""
        self._notification_channels[patient_id] = [
            NotificationChannel(
                channel_id=str(uuid4()),
                channel_type=ch["type"],
                destination=ch["destination"],
                is_active=ch.get("is_active", True),
                priority_threshold=AlertSeverity(ch.get("priority_threshold", 2)),
            )
            for ch in channels
        ]

    # Message handlers

    async def _handle_create_alert(self, message: Message) -> Message:
        """Handle create alert request."""
        content = message.content
        try:
            alert = await self.create_alert(
                patient_id=content["patient_id"],
                category=AlertCategory(content["category"]),
                severity=AlertSeverity(content["severity"]),
                title=content["title"],
                message=content["message"],
                source_agent=content.get("source_agent", ""),
                data=content.get("data"),
                actions=content.get("actions"),
                expires_in_hours=content.get("expires_in_hours"),
            )
            return message.create_response(
                self.agent_id,
                {
                    "success": True,
                    "alert_id": alert.alert_id,
                    "severity": alert.severity.name,
                }
            )
        except Exception as e:
            return message.create_response(
                self.agent_id,
                {"success": False, "error": str(e)}
            )

    async def _handle_acknowledge_alert(self, message: Message) -> Message:
        """Handle acknowledge alert request."""
        content = message.content
        success = await self.acknowledge_alert(
            patient_id=content["patient_id"],
            alert_id=content["alert_id"],
            acknowledged_by=content.get("acknowledged_by", ""),
        )
        return message.create_response(
            self.agent_id,
            {"success": success}
        )

    async def _handle_resolve_alert(self, message: Message) -> Message:
        """Handle resolve alert request."""
        content = message.content
        success = await self.resolve_alert(
            patient_id=content["patient_id"],
            alert_id=content["alert_id"],
            resolution_notes=content.get("resolution_notes", ""),
        )
        return message.create_response(
            self.agent_id,
            {"success": success}
        )

    async def _handle_get_active_alerts(self, message: Message) -> Message:
        """Handle get active alerts request."""
        content = message.content
        patient_id = content.get("patient_id")
        category = AlertCategory(content["category"]) if content.get("category") else None
        min_severity = AlertSeverity(content["min_severity"]) if content.get("min_severity") else None

        alerts = self.get_active_alerts(patient_id, category, min_severity)

        return message.create_response(
            self.agent_id,
            {
                "success": True,
                "alerts": [
                    {
                        "alert_id": a.alert_id,
                        "category": a.category.value,
                        "severity": a.severity.value,
                        "severity_name": a.severity.name,
                        "title": a.title,
                        "message": a.message,
                        "status": a.status.value,
                        "created_at": a.created_at.isoformat(),
                        "actions": a.actions,
                    }
                    for a in alerts
                ],
            }
        )

    async def _handle_get_alert_history(self, message: Message) -> Message:
        """Handle get alert history request."""
        content = message.content
        patient_id = content.get("patient_id")
        limit = content.get("limit", 50)

        history = self._alert_history.get(patient_id, [])[-limit:]

        return message.create_response(
            self.agent_id,
            {
                "success": True,
                "alerts": [
                    {
                        "alert_id": a.alert_id,
                        "category": a.category.value,
                        "severity": a.severity.value,
                        "title": a.title,
                        "status": a.status.value,
                        "created_at": a.created_at.isoformat(),
                        "resolved_at": a.resolved_at.isoformat() if a.resolved_at else None,
                    }
                    for a in history
                ],
            }
        )

    async def _handle_configure_notifications(self, message: Message) -> Message:
        """Handle configure notifications request."""
        content = message.content
        patient_id = content.get("patient_id")
        channels = content.get("channels", [])

        self.configure_notifications(patient_id, channels)

        return message.create_response(
            self.agent_id,
            {"success": True, "message": "Notifications configured"}
        )

    async def _handle_trigger_emergency(self, message: Message) -> Message:
        """Handle trigger emergency request."""
        content = message.content
        alert = await self.trigger_emergency(
            patient_id=content["patient_id"],
            reason=content["reason"],
            location=content.get("location"),
        )
        return message.create_response(
            self.agent_id,
            {
                "success": True,
                "alert_id": alert.alert_id,
                "message": "Emergency response initiated",
            }
        )
