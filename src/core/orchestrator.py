"""Agent orchestrator for coordinating the multi-agent system."""

import asyncio
import logging
from datetime import datetime
from typing import Any

from .base_agent import AgentCapability, AgentState, BaseAgent
from .context import HealthContext, PatientProfile
from .event_bus import Event, EventBus, EventType
from .message import Message, MessagePriority, MessageType

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Central orchestrator for the multi-agent health monitoring system.

    Responsibilities:
    - Agent lifecycle management
    - Message routing between agents
    - Event bus management
    - Health context distribution
    - System-wide coordination
    """

    def __init__(self):
        self.agents: dict[str, BaseAgent] = {}
        self.event_bus = EventBus()
        self._health_contexts: dict[str, HealthContext] = {}
        self._running = False
        self._coordination_task: asyncio.Task | None = None

        # Agent routing by capability
        self._capability_map: dict[AgentCapability, list[str]] = {}

        # Pending responses for request-response correlation
        self._pending_requests: dict[str, asyncio.Future] = {}

        logger.info("Agent orchestrator initialized")

    async def start(self) -> None:
        """Start the orchestrator and all registered agents."""
        if self._running:
            logger.warning("Orchestrator is already running")
            return

        self._running = True

        # Start event bus
        await self.event_bus.start()

        # Subscribe to system events
        self.event_bus.subscribe(
            EventType.AGENT_ERROR,
            self._handle_agent_error,
            "orchestrator"
        )

        # Start all registered agents
        for agent in self.agents.values():
            await agent.start()

        # Start coordination loop
        self._coordination_task = asyncio.create_task(self._coordination_loop())

        logger.info(f"Orchestrator started with {len(self.agents)} agents")

    async def stop(self) -> None:
        """Stop the orchestrator and all agents."""
        self._running = False

        # Stop coordination loop
        if self._coordination_task:
            self._coordination_task.cancel()
            try:
                await self._coordination_task
            except asyncio.CancelledError:
                pass

        # Stop all agents
        for agent in self.agents.values():
            await agent.stop()

        # Stop event bus
        await self.event_bus.stop()

        logger.info("Orchestrator stopped")

    def register_agent(self, agent: BaseAgent) -> None:
        """
        Register an agent with the orchestrator.

        Args:
            agent: The agent to register
        """
        self.agents[agent.agent_id] = agent
        agent.set_event_bus(self.event_bus)

        # Update capability map
        for capability in agent.capabilities:
            if capability not in self._capability_map:
                self._capability_map[capability] = []
            self._capability_map[capability].append(agent.agent_id)

        # Share existing health contexts
        for context in self._health_contexts.values():
            agent.register_health_context(context)

        logger.info(f"Registered agent: {agent.name} ({agent.agent_id})")

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent."""
        if agent_id in self.agents:
            agent = self.agents.pop(agent_id)

            # Remove from capability map
            for capability in agent.capabilities:
                if capability in self._capability_map:
                    self._capability_map[capability] = [
                        aid for aid in self._capability_map[capability]
                        if aid != agent_id
                    ]

            logger.info(f"Unregistered agent: {agent.name}")

    def register_patient(self, profile: PatientProfile) -> HealthContext:
        """
        Register a patient and create their health context.

        Args:
            profile: The patient's profile

        Returns:
            The created health context
        """
        context = HealthContext(
            patient_id=profile.patient_id,
            profile=profile
        )
        self._health_contexts[profile.patient_id] = context

        # Distribute to all agents
        for agent in self.agents.values():
            agent.register_health_context(context)

        logger.info(f"Registered patient: {profile.first_name} {profile.last_name}")
        return context

    def get_health_context(self, patient_id: str) -> HealthContext | None:
        """Get health context for a patient."""
        return self._health_contexts.get(patient_id)

    async def send_message(
        self,
        sender_id: str,
        recipient_id: str,
        message_type: MessageType,
        content: dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL,
        wait_response: bool = False,
        timeout: float = 30.0
    ) -> Message | None:
        """
        Send a message between agents.

        Args:
            sender_id: ID of the sending agent
            recipient_id: ID of the recipient agent
            message_type: Type of message
            content: Message content
            priority: Message priority
            wait_response: Whether to wait for a response
            timeout: Response timeout in seconds

        Returns:
            Response message if wait_response is True
        """
        if recipient_id not in self.agents:
            logger.error(f"Unknown recipient agent: {recipient_id}")
            return None

        message = Message(
            sender_id=sender_id,
            recipient_id=recipient_id,
            message_type=message_type,
            content=content,
            priority=priority
        )

        recipient = self.agents[recipient_id]
        await recipient.receive_message(message)

        if wait_response:
            return await self._wait_for_response(message.message_id, timeout)

        return None

    async def broadcast_message(
        self,
        sender_id: str,
        message_type: MessageType,
        content: dict[str, Any],
        capabilities: list[AgentCapability] | None = None
    ) -> None:
        """
        Broadcast a message to multiple agents.

        Args:
            sender_id: ID of the sending agent
            message_type: Type of message
            content: Message content
            capabilities: If provided, only send to agents with these capabilities
        """
        message = Message(
            sender_id=sender_id,
            recipient_id=None,
            message_type=MessageType.BROADCAST,
            content=content
        )

        recipients = []
        if capabilities:
            for cap in capabilities:
                recipients.extend(self._capability_map.get(cap, []))
            recipients = list(set(recipients))
        else:
            recipients = list(self.agents.keys())

        # Remove sender from recipients
        recipients = [r for r in recipients if r != sender_id]

        for recipient_id in recipients:
            msg_copy = Message(
                sender_id=message.sender_id,
                recipient_id=recipient_id,
                message_type=message.message_type,
                content=message.content.copy(),
                priority=message.priority
            )
            await self.agents[recipient_id].receive_message(msg_copy)

    async def request_capability(
        self,
        requester_id: str,
        capability: AgentCapability,
        request_content: dict[str, Any],
        timeout: float = 30.0
    ) -> list[Message]:
        """
        Request service from agents with a specific capability.

        Args:
            requester_id: ID of the requesting agent
            capability: Required capability
            request_content: Request content
            timeout: Response timeout

        Returns:
            List of response messages
        """
        agent_ids = self._capability_map.get(capability, [])

        if not agent_ids:
            logger.warning(f"No agents with capability: {capability.value}")
            return []

        responses = []
        for agent_id in agent_ids:
            response = await self.send_message(
                sender_id=requester_id,
                recipient_id=agent_id,
                message_type=MessageType.REQUEST,
                content=request_content,
                wait_response=True,
                timeout=timeout
            )
            if response:
                responses.append(response)

        return responses

    async def _wait_for_response(
        self,
        message_id: str,
        timeout: float
    ) -> Message | None:
        """Wait for a response to a message."""
        future: asyncio.Future = asyncio.Future()
        self._pending_requests[message_id] = future

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            logger.warning(f"Timeout waiting for response to {message_id}")
            return None
        finally:
            self._pending_requests.pop(message_id, None)

    def complete_request(self, correlation_id: str, response: Message) -> None:
        """Complete a pending request with a response."""
        if correlation_id in self._pending_requests:
            self._pending_requests[correlation_id].set_result(response)

    async def _handle_agent_error(self, event: Event) -> None:
        """Handle agent error events."""
        agent_id = event.data.get("agent_id")
        error = event.data.get("error")
        logger.error(f"Agent error reported: {agent_id} - {error}")

        # Could implement recovery logic here
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            if agent.state == AgentState.ERROR:
                # Attempt restart
                logger.info(f"Attempting to restart agent {agent.name}")
                await agent.stop()
                await asyncio.sleep(1)
                await agent.start()

    async def _coordination_loop(self) -> None:
        """Main coordination loop for system-wide tasks."""
        while self._running:
            try:
                # Periodic health checks
                await self._check_agent_health()

                # Context synchronization
                await self._sync_contexts()

                await asyncio.sleep(5)  # Run every 5 seconds

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Coordination loop error: {e}")

    async def _check_agent_health(self) -> None:
        """Check health of all agents."""
        for agent_id, agent in self.agents.items():
            if agent.state == AgentState.ERROR:
                await self.event_bus.publish(Event(
                    event_type=EventType.AGENT_ERROR,
                    source_agent_id="orchestrator",
                    data={"agent_id": agent_id, "state": agent.state.value}
                ))

    async def _sync_contexts(self) -> None:
        """Synchronize health contexts across agents."""
        # Contexts are shared by reference, but we can trigger updates
        for context in self._health_contexts.values():
            context.last_updated = datetime.utcnow()

    def get_system_status(self) -> dict[str, Any]:
        """Get overall system status."""
        agent_statuses = {
            agent_id: agent.get_status()
            for agent_id, agent in self.agents.items()
        }

        return {
            "running": self._running,
            "agents_count": len(self.agents),
            "patients_count": len(self._health_contexts),
            "agents": agent_statuses,
            "capabilities": {
                cap.value: len(agents)
                for cap, agents in self._capability_map.items()
            },
            "event_bus_active": self.event_bus._running,
        }

    def get_agents_by_capability(
        self,
        capability: AgentCapability
    ) -> list[BaseAgent]:
        """Get all agents with a specific capability."""
        agent_ids = self._capability_map.get(capability, [])
        return [self.agents[aid] for aid in agent_ids if aid in self.agents]
