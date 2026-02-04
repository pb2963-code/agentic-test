"""Event bus for publish-subscribe communication between agents."""

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine
from uuid import uuid4

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of events in the health monitoring system."""

    # Vital signs events
    VITAL_READING = "vital_reading"
    VITAL_ANOMALY = "vital_anomaly"
    VITAL_TREND_CHANGE = "vital_trend_change"

    # Medication events
    MEDICATION_REMINDER = "medication_reminder"
    MEDICATION_TAKEN = "medication_taken"
    MEDICATION_MISSED = "medication_missed"
    MEDICATION_INTERACTION = "medication_interaction"

    # Symptom events
    SYMPTOM_REPORTED = "symptom_reported"
    SYMPTOM_PATTERN = "symptom_pattern"
    SYMPTOM_ESCALATION = "symptom_escalation"

    # Wellness events
    ACTIVITY_UPDATE = "activity_update"
    SLEEP_DATA = "sleep_data"
    NUTRITION_LOG = "nutrition_log"
    WELLNESS_GOAL_PROGRESS = "wellness_goal_progress"

    # Alert events
    HEALTH_ALERT = "health_alert"
    EMERGENCY_ALERT = "emergency_alert"
    ALERT_ACKNOWLEDGED = "alert_acknowledged"

    # System events
    AGENT_STARTED = "agent_started"
    AGENT_STOPPED = "agent_stopped"
    AGENT_ERROR = "agent_error"
    SYSTEM_STATUS = "system_status"

    # Analysis events
    HEALTH_INSIGHT = "health_insight"
    RISK_ASSESSMENT = "risk_assessment"
    RECOMMENDATION = "recommendation"


@dataclass
class Event:
    """
    Event for the publish-subscribe system.

    Events are used for loose coupling between agents,
    allowing them to react to system-wide occurrences.
    """

    event_type: EventType
    source_agent_id: str
    data: dict[str, Any]
    event_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    patient_id: str | None = None
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source_agent_id": self.source_agent_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "patient_id": self.patient_id,
            "tags": self.tags,
        }


# Type alias for event handlers
EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """
    Asynchronous event bus for agent communication.

    Provides publish-subscribe functionality for loose coupling
    between agents in the health monitoring system.
    """

    def __init__(self, max_queue_size: int = 10000):
        self._subscribers: dict[EventType, list[tuple[str, EventHandler]]] = defaultdict(list)
        self._event_queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=max_queue_size)
        self._event_history: list[Event] = []
        self._max_history = 1000
        self._running = False
        self._processor_task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """Start the event bus processor."""
        if self._running:
            return

        self._running = True
        self._processor_task = asyncio.create_task(self._process_events())
        logger.info("Event bus started")

    async def stop(self) -> None:
        """Stop the event bus processor."""
        self._running = False

        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass

        logger.info("Event bus stopped")

    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler,
        subscriber_id: str
    ) -> None:
        """
        Subscribe to an event type.

        Args:
            event_type: The type of event to subscribe to
            handler: Async function to handle the event
            subscriber_id: Identifier for the subscriber
        """
        self._subscribers[event_type].append((subscriber_id, handler))
        logger.debug(f"Subscriber {subscriber_id} registered for {event_type.value}")

    def unsubscribe(self, event_type: EventType, subscriber_id: str) -> None:
        """Unsubscribe from an event type."""
        self._subscribers[event_type] = [
            (sid, handler) for sid, handler in self._subscribers[event_type]
            if sid != subscriber_id
        ]

    async def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event: The event to publish
        """
        await self._event_queue.put(event)

        async with self._lock:
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history = self._event_history[-self._max_history:]

    async def _process_events(self) -> None:
        """Process events from the queue."""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=1.0
                )
                await self._dispatch_event(event)
                self._event_queue.task_done()
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing event: {e}")

    async def _dispatch_event(self, event: Event) -> None:
        """Dispatch event to all subscribers."""
        handlers = self._subscribers.get(event.event_type, [])

        if not handlers:
            logger.debug(f"No handlers for event type: {event.event_type.value}")
            return

        tasks = []
        for subscriber_id, handler in handlers:
            tasks.append(self._safe_call_handler(subscriber_id, handler, event))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _safe_call_handler(
        self,
        subscriber_id: str,
        handler: EventHandler,
        event: Event
    ) -> None:
        """Safely call an event handler."""
        try:
            await handler(event)
        except Exception as e:
            logger.error(
                f"Handler error for {subscriber_id} on {event.event_type.value}: {e}"
            )

    def get_recent_events(
        self,
        event_type: EventType | None = None,
        patient_id: str | None = None,
        limit: int = 100
    ) -> list[Event]:
        """Get recent events with optional filtering."""
        events = self._event_history

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if patient_id:
            events = [e for e in events if e.patient_id == patient_id]

        return events[-limit:]
