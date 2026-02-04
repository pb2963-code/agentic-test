"""Vital signs monitoring agent."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from ..core.base_agent import AgentCapability, BaseAgent
from ..core.context import RiskLevel
from ..core.event_bus import Event, EventType
from ..core.message import Message, MessageType

logger = logging.getLogger(__name__)


class VitalType(Enum):
    """Types of vital signs."""

    HEART_RATE = "heart_rate"
    BLOOD_PRESSURE_SYSTOLIC = "blood_pressure_systolic"
    BLOOD_PRESSURE_DIASTOLIC = "blood_pressure_diastolic"
    TEMPERATURE = "temperature"
    OXYGEN_SATURATION = "oxygen_saturation"
    RESPIRATORY_RATE = "respiratory_rate"
    BLOOD_GLUCOSE = "blood_glucose"
    WEIGHT = "weight"


@dataclass
class VitalThresholds:
    """Thresholds for vital sign monitoring."""

    vital_type: VitalType
    low_critical: float
    low_warning: float
    normal_low: float
    normal_high: float
    high_warning: float
    high_critical: float


# Default thresholds for adult patients
DEFAULT_THRESHOLDS: dict[VitalType, VitalThresholds] = {
    VitalType.HEART_RATE: VitalThresholds(
        VitalType.HEART_RATE, 40, 50, 60, 100, 110, 150
    ),
    VitalType.BLOOD_PRESSURE_SYSTOLIC: VitalThresholds(
        VitalType.BLOOD_PRESSURE_SYSTOLIC, 70, 90, 90, 120, 140, 180
    ),
    VitalType.BLOOD_PRESSURE_DIASTOLIC: VitalThresholds(
        VitalType.BLOOD_PRESSURE_DIASTOLIC, 40, 50, 60, 80, 90, 120
    ),
    VitalType.TEMPERATURE: VitalThresholds(
        VitalType.TEMPERATURE, 35.0, 36.0, 36.1, 37.2, 38.0, 40.0
    ),
    VitalType.OXYGEN_SATURATION: VitalThresholds(
        VitalType.OXYGEN_SATURATION, 85, 90, 95, 100, 100, 100
    ),
    VitalType.RESPIRATORY_RATE: VitalThresholds(
        VitalType.RESPIRATORY_RATE, 8, 10, 12, 20, 24, 30
    ),
    VitalType.BLOOD_GLUCOSE: VitalThresholds(
        VitalType.BLOOD_GLUCOSE, 50, 70, 70, 140, 180, 300
    ),
}


@dataclass
class VitalReading:
    """A single vital sign reading."""

    vital_type: VitalType
    value: float
    unit: str
    timestamp: datetime
    patient_id: str
    device_id: str | None = None
    notes: str = ""


class VitalSignsAgent(BaseAgent):
    """
    Agent responsible for monitoring patient vital signs.

    Capabilities:
    - Real-time vital sign monitoring
    - Anomaly detection
    - Trend analysis
    - Alert generation for abnormal readings
    - Historical data analysis
    """

    def __init__(self, agent_id: str | None = None):
        super().__init__(
            agent_id=agent_id,
            name="VitalSignsAgent",
            description="Monitors and analyzes patient vital signs in real-time",
            capabilities=[
                AgentCapability.VITAL_MONITORING,
                AgentCapability.DATA_ANALYSIS,
            ]
        )

        # Patient-specific thresholds (patient_id -> thresholds)
        self._patient_thresholds: dict[str, dict[VitalType, VitalThresholds]] = {}

        # Recent readings history (patient_id -> vital_type -> readings)
        self._readings_history: dict[str, dict[VitalType, list[VitalReading]]] = {}

        # Maximum readings to keep per vital type
        self._max_history = 1000

        # Subscribe to relevant events
        self.subscribe_to_event(EventType.VITAL_READING)
        self.subscribe_to_event(EventType.SYSTEM_STATUS)

    async def on_start(self) -> None:
        """Initialize agent-specific resources."""
        logger.info(f"{self.name} started - monitoring vital signs")

    async def handle_message(self, message: Message) -> Message | None:
        """Handle incoming messages."""
        content = message.content
        action = content.get("action")

        if action == "record_vital":
            return await self._handle_record_vital(message)
        elif action == "get_current_vitals":
            return await self._handle_get_current_vitals(message)
        elif action == "get_vital_history":
            return await self._handle_get_vital_history(message)
        elif action == "set_thresholds":
            return await self._handle_set_thresholds(message)
        elif action == "analyze_trends":
            return await self._handle_analyze_trends(message)
        else:
            logger.warning(f"Unknown action: {action}")
            return message.create_response(
                self.agent_id,
                {"error": f"Unknown action: {action}"}
            )

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events."""
        if event.event_type == EventType.VITAL_READING:
            await self._process_vital_event(event)

    async def record_vital(
        self,
        patient_id: str,
        vital_type: VitalType,
        value: float,
        unit: str,
        device_id: str | None = None,
        notes: str = ""
    ) -> dict[str, Any]:
        """
        Record a new vital sign reading.

        Args:
            patient_id: Patient identifier
            vital_type: Type of vital sign
            value: The reading value
            unit: Unit of measurement
            device_id: Optional device identifier
            notes: Optional notes

        Returns:
            Analysis result including any alerts
        """
        reading = VitalReading(
            vital_type=vital_type,
            value=value,
            unit=unit,
            timestamp=datetime.utcnow(),
            patient_id=patient_id,
            device_id=device_id,
            notes=notes
        )

        # Store reading
        self._store_reading(reading)

        # Update health context
        context = self.get_health_context(patient_id)
        if context:
            context.update_vitals(
                vital_type.value,
                {"value": value, "unit": unit},
                reading.timestamp
            )

        # Analyze reading
        analysis = self._analyze_reading(reading)

        # Publish events based on analysis
        await self._publish_reading_events(reading, analysis)

        return analysis

    def _store_reading(self, reading: VitalReading) -> None:
        """Store a vital reading in history."""
        patient_id = reading.patient_id
        vital_type = reading.vital_type

        if patient_id not in self._readings_history:
            self._readings_history[patient_id] = {}

        if vital_type not in self._readings_history[patient_id]:
            self._readings_history[patient_id][vital_type] = []

        history = self._readings_history[patient_id][vital_type]
        history.append(reading)

        # Trim history if needed
        if len(history) > self._max_history:
            self._readings_history[patient_id][vital_type] = history[-self._max_history:]

    def _analyze_reading(self, reading: VitalReading) -> dict[str, Any]:
        """Analyze a vital reading against thresholds."""
        patient_id = reading.patient_id
        vital_type = reading.vital_type
        value = reading.value

        # Get thresholds (patient-specific or default)
        thresholds = self._get_thresholds(patient_id, vital_type)

        if not thresholds:
            return {
                "status": "unknown",
                "message": f"No thresholds defined for {vital_type.value}"
            }

        # Determine status
        status = "normal"
        risk_level = RiskLevel.LOW
        alert_type = None

        if value <= thresholds.low_critical or value >= thresholds.high_critical:
            status = "critical"
            risk_level = RiskLevel.CRITICAL
            alert_type = "critical"
        elif value <= thresholds.low_warning or value >= thresholds.high_warning:
            status = "warning"
            risk_level = RiskLevel.HIGH
            alert_type = "warning"
        elif value < thresholds.normal_low or value > thresholds.normal_high:
            status = "borderline"
            risk_level = RiskLevel.MODERATE

        # Trend analysis
        trend = self._calculate_trend(patient_id, vital_type)

        result = {
            "status": status,
            "risk_level": risk_level.value,
            "value": value,
            "vital_type": vital_type.value,
            "thresholds": {
                "low_critical": thresholds.low_critical,
                "low_warning": thresholds.low_warning,
                "normal_range": [thresholds.normal_low, thresholds.normal_high],
                "high_warning": thresholds.high_warning,
                "high_critical": thresholds.high_critical,
            },
            "trend": trend,
            "alert_type": alert_type,
            "timestamp": reading.timestamp.isoformat(),
        }

        # Update context risk level
        context = self.get_health_context(patient_id)
        if context:
            context.update_risk_level(f"vital_{vital_type.value}", risk_level)

        return result

    def _get_thresholds(
        self,
        patient_id: str,
        vital_type: VitalType
    ) -> VitalThresholds | None:
        """Get thresholds for a patient and vital type."""
        # Check patient-specific thresholds
        if patient_id in self._patient_thresholds:
            if vital_type in self._patient_thresholds[patient_id]:
                return self._patient_thresholds[patient_id][vital_type]

        # Fall back to defaults
        return DEFAULT_THRESHOLDS.get(vital_type)

    def _calculate_trend(
        self,
        patient_id: str,
        vital_type: VitalType,
        window_hours: int = 24
    ) -> dict[str, Any]:
        """Calculate trend for a vital sign over a time window."""
        if patient_id not in self._readings_history:
            return {"direction": "insufficient_data", "change_percent": 0}

        if vital_type not in self._readings_history[patient_id]:
            return {"direction": "insufficient_data", "change_percent": 0}

        readings = self._readings_history[patient_id][vital_type]
        cutoff = datetime.utcnow() - timedelta(hours=window_hours)

        recent = [r for r in readings if r.timestamp >= cutoff]

        if len(recent) < 3:
            return {"direction": "insufficient_data", "change_percent": 0}

        # Simple linear trend
        first_half = recent[:len(recent)//2]
        second_half = recent[len(recent)//2:]

        avg_first = sum(r.value for r in first_half) / len(first_half)
        avg_second = sum(r.value for r in second_half) / len(second_half)

        if avg_first == 0:
            change_percent = 0
        else:
            change_percent = ((avg_second - avg_first) / avg_first) * 100

        if change_percent > 5:
            direction = "increasing"
        elif change_percent < -5:
            direction = "decreasing"
        else:
            direction = "stable"

        return {
            "direction": direction,
            "change_percent": round(change_percent, 2),
            "samples": len(recent),
            "window_hours": window_hours,
        }

    async def _publish_reading_events(
        self,
        reading: VitalReading,
        analysis: dict[str, Any]
    ) -> None:
        """Publish events based on reading analysis."""
        # Always publish the reading event
        await self._publish_event(
            EventType.VITAL_READING,
            {
                "vital_type": reading.vital_type.value,
                "value": reading.value,
                "unit": reading.unit,
                "analysis": analysis,
            },
            patient_id=reading.patient_id,
            tags=[reading.vital_type.value, analysis["status"]]
        )

        # Publish anomaly if detected
        if analysis["status"] in ["warning", "critical"]:
            await self._publish_event(
                EventType.VITAL_ANOMALY,
                {
                    "vital_type": reading.vital_type.value,
                    "value": reading.value,
                    "status": analysis["status"],
                    "risk_level": analysis["risk_level"],
                },
                patient_id=reading.patient_id,
                tags=["anomaly", analysis["status"]]
            )

        # Publish trend change if significant
        trend = analysis.get("trend", {})
        if abs(trend.get("change_percent", 0)) > 10:
            await self._publish_event(
                EventType.VITAL_TREND_CHANGE,
                {
                    "vital_type": reading.vital_type.value,
                    "trend": trend,
                },
                patient_id=reading.patient_id,
                tags=["trend", trend.get("direction", "unknown")]
            )

    async def _process_vital_event(self, event: Event) -> None:
        """Process a vital reading event from another source."""
        data = event.data
        patient_id = event.patient_id

        if not patient_id:
            return

        try:
            vital_type = VitalType(data.get("vital_type"))
            value = float(data.get("value", 0))
            unit = data.get("unit", "")

            await self.record_vital(
                patient_id=patient_id,
                vital_type=vital_type,
                value=value,
                unit=unit,
                device_id=data.get("device_id")
            )
        except (ValueError, TypeError) as e:
            logger.error(f"Error processing vital event: {e}")

    async def _handle_record_vital(self, message: Message) -> Message:
        """Handle record vital request."""
        content = message.content
        try:
            result = await self.record_vital(
                patient_id=content["patient_id"],
                vital_type=VitalType(content["vital_type"]),
                value=float(content["value"]),
                unit=content.get("unit", ""),
                device_id=content.get("device_id"),
                notes=content.get("notes", "")
            )
            return message.create_response(self.agent_id, {"success": True, "analysis": result})
        except Exception as e:
            return message.create_response(self.agent_id, {"success": False, "error": str(e)})

    async def _handle_get_current_vitals(self, message: Message) -> Message:
        """Handle get current vitals request."""
        patient_id = message.content.get("patient_id")
        context = self.get_health_context(patient_id)

        if context:
            return message.create_response(
                self.agent_id,
                {"success": True, "vitals": context.current_vitals}
            )
        return message.create_response(
            self.agent_id,
            {"success": False, "error": "Patient not found"}
        )

    async def _handle_get_vital_history(self, message: Message) -> Message:
        """Handle get vital history request."""
        content = message.content
        patient_id = content.get("patient_id")
        vital_type_str = content.get("vital_type")
        limit = content.get("limit", 100)

        if patient_id not in self._readings_history:
            return message.create_response(
                self.agent_id,
                {"success": True, "history": []}
            )

        history = []
        patient_history = self._readings_history[patient_id]

        if vital_type_str:
            vital_type = VitalType(vital_type_str)
            readings = patient_history.get(vital_type, [])
            history = [
                {
                    "vital_type": r.vital_type.value,
                    "value": r.value,
                    "unit": r.unit,
                    "timestamp": r.timestamp.isoformat(),
                }
                for r in readings[-limit:]
            ]
        else:
            for vt, readings in patient_history.items():
                for r in readings[-limit:]:
                    history.append({
                        "vital_type": r.vital_type.value,
                        "value": r.value,
                        "unit": r.unit,
                        "timestamp": r.timestamp.isoformat(),
                    })

        return message.create_response(
            self.agent_id,
            {"success": True, "history": history}
        )

    async def _handle_set_thresholds(self, message: Message) -> Message:
        """Handle set thresholds request."""
        content = message.content
        patient_id = content.get("patient_id")
        thresholds_data = content.get("thresholds", {})

        if patient_id not in self._patient_thresholds:
            self._patient_thresholds[patient_id] = {}

        for vt_str, values in thresholds_data.items():
            vital_type = VitalType(vt_str)
            self._patient_thresholds[patient_id][vital_type] = VitalThresholds(
                vital_type=vital_type,
                low_critical=values["low_critical"],
                low_warning=values["low_warning"],
                normal_low=values["normal_low"],
                normal_high=values["normal_high"],
                high_warning=values["high_warning"],
                high_critical=values["high_critical"],
            )

        return message.create_response(
            self.agent_id,
            {"success": True, "message": "Thresholds updated"}
        )

    async def _handle_analyze_trends(self, message: Message) -> Message:
        """Handle analyze trends request."""
        content = message.content
        patient_id = content.get("patient_id")
        window_hours = content.get("window_hours", 24)

        trends = {}
        if patient_id in self._readings_history:
            for vital_type in self._readings_history[patient_id]:
                trends[vital_type.value] = self._calculate_trend(
                    patient_id, vital_type, window_hours
                )

        return message.create_response(
            self.agent_id,
            {"success": True, "trends": trends}
        )
