"""Base agent class for the multi-agent health monitoring system."""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from .context import HealthContext
from .event_bus import Event, EventBus, EventType
from .message import Message, MessagePriority, MessageType

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """Operational states for an agent."""

    INITIALIZING = "initializing"
    READY = "ready"
    PROCESSING = "processing"
    WAITING = "waiting"
    PAUSED = "paused"
    ERROR = "error"
    STOPPED = "stopped"


class AgentCapability(Enum):
    """Capabilities that agents can have."""

    VITAL_MONITORING = "vital_monitoring"
    MEDICATION_MANAGEMENT = "medication_management"
    SYMPTOM_ANALYSIS = "symptom_analysis"
    WELLNESS_TRACKING = "wellness_tracking"
    ALERT_MANAGEMENT = "alert_management"
    DATA_ANALYSIS = "data_analysis"
    RECOMMENDATION = "recommendation"
    COORDINATION = "coordination"
    EMERGENCY_RESPONSE = "emergency_response"


@dataclass
class AgentMetrics:
    """Performance metrics for an agent."""

    messages_processed: int = 0
    events_published: int = 0
    events_handled: int = 0
    errors_count: int = 0
    avg_processing_time_ms: float = 0.0
    last_active: datetime = field(default_factory=datetime.utcnow)

    def record_processing(self, processing_time_ms: float) -> None:
        """Record a processing operation."""
        total = self.avg_processing_time_ms * self.messages_processed
        self.messages_processed += 1
        self.avg_processing_time_ms = (total + processing_time_ms) / self.messages_processed
        self.last_active = datetime.utcnow()


class BaseAgent(ABC):
    """
    Abstract base class for all health monitoring agents.

    Provides common functionality for:
    - Message handling and routing
    - Event publishing and subscribing
    - State management
    - Health context access
    - Metrics collection
    """

    def __init__(
        self,
        agent_id: str | None = None,
        name: str = "BaseAgent",
        description: str = "",
        capabilities: list[AgentCapability] | None = None,
    ):
        self.agent_id = agent_id or str(uuid4())
        self.name = name
        self.description = description
        self.capabilities = capabilities or []
        self.state = AgentState.INITIALIZING
        self.metrics = AgentMetrics()

        self._event_bus: EventBus | None = None
        self._message_queue: asyncio.Queue[Message] = asyncio.Queue()
        self._health_contexts: dict[str, HealthContext] = {}
        self._running = False
        self._task: asyncio.Task | None = None

        # Subscribed event types
        self._subscribed_events: list[EventType] = []

        logger.info(f"Agent {self.name} ({self.agent_id}) initialized")

    def set_event_bus(self, event_bus: EventBus) -> None:
        """Set the event bus for this agent."""
        self._event_bus = event_bus

    def register_health_context(self, context: HealthContext) -> None:
        """Register a patient's health context with this agent."""
        self._health_contexts[context.patient_id] = context
        logger.debug(f"Agent {self.name} registered context for patient {context.patient_id}")

    def get_health_context(self, patient_id: str) -> HealthContext | None:
        """Get health context for a patient."""
        return self._health_contexts.get(patient_id)

    async def start(self) -> None:
        """Start the agent."""
        if self._running:
            logger.warning(f"Agent {self.name} is already running")
            return

        self._running = True
        self.state = AgentState.READY

        # Subscribe to relevant events
        if self._event_bus:
            for event_type in self._subscribed_events:
                self._event_bus.subscribe(
                    event_type,
                    self._handle_event,
                    self.agent_id
                )

        # Start message processing loop
        self._task = asyncio.create_task(self._process_messages())

        # Call agent-specific initialization
        await self.on_start()

        # Publish agent started event
        await self._publish_event(
            EventType.AGENT_STARTED,
            {"agent_name": self.name, "capabilities": [c.value for c in self.capabilities]}
        )

        logger.info(f"Agent {self.name} started")

    async def stop(self) -> None:
        """Stop the agent."""
        self._running = False
        self.state = AgentState.STOPPED

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        # Unsubscribe from events
        if self._event_bus:
            for event_type in self._subscribed_events:
                self._event_bus.unsubscribe(event_type, self.agent_id)

        # Call agent-specific cleanup
        await self.on_stop()

        # Publish agent stopped event
        await self._publish_event(
            EventType.AGENT_STOPPED,
            {"agent_name": self.name}
        )

        logger.info(f"Agent {self.name} stopped")

    async def send_message(self, message: Message) -> None:
        """Send a message to another agent."""
        await self._message_queue.put(message)

    async def receive_message(self, message: Message) -> None:
        """Receive and queue a message for processing."""
        if message.is_expired():
            logger.warning(f"Received expired message {message.message_id}")
            return
        await self._message_queue.put(message)

    async def _process_messages(self) -> None:
        """Process messages from the queue."""
        while self._running:
            try:
                message = await asyncio.wait_for(
                    self._message_queue.get(),
                    timeout=1.0
                )

                self.state = AgentState.PROCESSING
                start_time = datetime.utcnow()

                try:
                    response = await self.handle_message(message)

                    if response and message.message_type == MessageType.REQUEST:
                        # Send response back
                        await self._route_response(response)

                except Exception as e:
                    logger.error(f"Error handling message in {self.name}: {e}")
                    self.metrics.errors_count += 1

                finally:
                    elapsed = (datetime.utcnow() - start_time).total_seconds() * 1000
                    self.metrics.record_processing(elapsed)
                    self.state = AgentState.READY
                    self._message_queue.task_done()

            except asyncio.TimeoutError:
                self.state = AgentState.WAITING
                continue

    async def _handle_event(self, event: Event) -> None:
        """Handle an incoming event."""
        try:
            self.metrics.events_handled += 1
            await self.handle_event(event)
        except Exception as e:
            logger.error(f"Error handling event in {self.name}: {e}")
            self.metrics.errors_count += 1

    async def _publish_event(
        self,
        event_type: EventType,
        data: dict[str, Any],
        patient_id: str | None = None,
        tags: list[str] | None = None
    ) -> None:
        """Publish an event to the event bus."""
        if not self._event_bus:
            logger.warning(f"Agent {self.name} has no event bus configured")
            return

        event = Event(
            event_type=event_type,
            source_agent_id=self.agent_id,
            data=data,
            patient_id=patient_id,
            tags=tags or []
        )

        await self._event_bus.publish(event)
        self.metrics.events_published += 1

    async def _route_response(self, message: Message) -> None:
        """Route a response message to the intended recipient."""
        # This would be handled by the orchestrator in a full implementation
        pass

    def subscribe_to_event(self, event_type: EventType) -> None:
        """Subscribe to an event type."""
        if event_type not in self._subscribed_events:
            self._subscribed_events.append(event_type)

            if self._event_bus and self._running:
                self._event_bus.subscribe(
                    event_type,
                    self._handle_event,
                    self.agent_id
                )

    def get_status(self) -> dict[str, Any]:
        """Get agent status information."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "state": self.state.value,
            "capabilities": [c.value for c in self.capabilities],
            "metrics": {
                "messages_processed": self.metrics.messages_processed,
                "events_published": self.metrics.events_published,
                "events_handled": self.metrics.events_handled,
                "errors_count": self.metrics.errors_count,
                "avg_processing_time_ms": round(self.metrics.avg_processing_time_ms, 2),
                "last_active": self.metrics.last_active.isoformat(),
            },
            "subscribed_events": [e.value for e in self._subscribed_events],
            "patients_monitored": len(self._health_contexts),
        }

    # Abstract methods to be implemented by specific agents

    @abstractmethod
    async def handle_message(self, message: Message) -> Message | None:
        """
        Handle an incoming message.

        Args:
            message: The message to handle

        Returns:
            Optional response message
        """
        pass

    @abstractmethod
    async def handle_event(self, event: Event) -> None:
        """
        Handle an incoming event.

        Args:
            event: The event to handle
        """
        pass

    async def on_start(self) -> None:
        """Called when the agent starts. Override for custom initialization."""
        pass

    async def on_stop(self) -> None:
        """Called when the agent stops. Override for custom cleanup."""
        pass
