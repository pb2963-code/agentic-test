"""Wellness tracking agent."""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any
from uuid import uuid4

from ..core.base_agent import AgentCapability, BaseAgent
from ..core.event_bus import Event, EventType
from ..core.message import Message

logger = logging.getLogger(__name__)


class ActivityType(Enum):
    """Types of physical activity."""

    WALKING = "walking"
    RUNNING = "running"
    CYCLING = "cycling"
    SWIMMING = "swimming"
    STRENGTH = "strength"
    YOGA = "yoga"
    SPORTS = "sports"
    HIKING = "hiking"
    OTHER = "other"


class SleepQuality(Enum):
    """Sleep quality ratings."""

    POOR = 1
    FAIR = 2
    GOOD = 3
    EXCELLENT = 4


class MoodLevel(Enum):
    """Mood levels."""

    VERY_LOW = 1
    LOW = 2
    NEUTRAL = 3
    GOOD = 4
    EXCELLENT = 5


@dataclass
class ActivityRecord:
    """Record of physical activity."""

    activity_id: str
    patient_id: str
    activity_type: ActivityType
    duration_minutes: int
    calories_burned: int | None
    distance_km: float | None
    heart_rate_avg: int | None
    heart_rate_max: int | None
    intensity: str  # low, moderate, vigorous
    notes: str = ""
    recorded_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SleepRecord:
    """Record of sleep data."""

    sleep_id: str
    patient_id: str
    sleep_start: datetime
    sleep_end: datetime
    total_hours: float
    deep_sleep_hours: float | None
    rem_sleep_hours: float | None
    awakenings: int
    quality: SleepQuality
    notes: str = ""
    recorded_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class NutritionRecord:
    """Record of nutrition/meal data."""

    nutrition_id: str
    patient_id: str
    meal_type: str  # breakfast, lunch, dinner, snack
    calories: int | None
    protein_g: float | None
    carbs_g: float | None
    fat_g: float | None
    fiber_g: float | None
    water_ml: int
    description: str = ""
    recorded_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class WellnessGoal:
    """A wellness goal."""

    goal_id: str
    patient_id: str
    goal_type: str  # steps, sleep, water, exercise, weight
    target_value: float
    current_value: float
    unit: str
    start_date: date
    end_date: date | None
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MoodRecord:
    """Record of mood/mental wellness."""

    mood_id: str
    patient_id: str
    mood_level: MoodLevel
    energy_level: int  # 1-10
    stress_level: int  # 1-10
    notes: str = ""
    factors: list[str] = field(default_factory=list)
    recorded_at: datetime = field(default_factory=datetime.utcnow)


class WellnessAgent(BaseAgent):
    """
    Agent responsible for wellness tracking.

    Capabilities:
    - Activity tracking
    - Sleep monitoring
    - Nutrition logging
    - Goal setting and tracking
    - Mood/mental wellness
    - Lifestyle recommendations
    """

    def __init__(self, agent_id: str | None = None):
        super().__init__(
            agent_id=agent_id,
            name="WellnessAgent",
            description="Tracks lifestyle and wellness data for holistic health",
            capabilities=[
                AgentCapability.WELLNESS_TRACKING,
                AgentCapability.RECOMMENDATION,
                AgentCapability.DATA_ANALYSIS,
            ]
        )

        # Activity records (patient_id -> list)
        self._activities: dict[str, list[ActivityRecord]] = {}

        # Sleep records (patient_id -> list)
        self._sleep_records: dict[str, list[SleepRecord]] = {}

        # Nutrition records (patient_id -> list)
        self._nutrition_records: dict[str, list[NutritionRecord]] = {}

        # Goals (patient_id -> goal_id -> goal)
        self._goals: dict[str, dict[str, WellnessGoal]] = {}

        # Mood records (patient_id -> list)
        self._mood_records: dict[str, list[MoodRecord]] = {}

        # Daily step counts (patient_id -> date -> steps)
        self._daily_steps: dict[str, dict[str, int]] = {}

        # Subscribe to events
        self.subscribe_to_event(EventType.ACTIVITY_UPDATE)
        self.subscribe_to_event(EventType.SLEEP_DATA)

    async def on_start(self) -> None:
        """Initialize agent."""
        logger.info(f"{self.name} started - tracking wellness")

    async def handle_message(self, message: Message) -> Message | None:
        """Handle incoming messages."""
        content = message.content
        action = content.get("action")

        handlers = {
            "log_activity": self._handle_log_activity,
            "log_sleep": self._handle_log_sleep,
            "log_nutrition": self._handle_log_nutrition,
            "log_mood": self._handle_log_mood,
            "log_steps": self._handle_log_steps,
            "set_goal": self._handle_set_goal,
            "get_goals": self._handle_get_goals,
            "get_daily_summary": self._handle_get_daily_summary,
            "get_weekly_summary": self._handle_get_weekly_summary,
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
        """Handle incoming events."""
        if event.event_type == EventType.ACTIVITY_UPDATE:
            logger.debug(f"Activity update for patient {event.patient_id}")
        elif event.event_type == EventType.SLEEP_DATA:
            logger.debug(f"Sleep data for patient {event.patient_id}")

    async def log_activity(
        self,
        patient_id: str,
        activity_type: ActivityType,
        duration_minutes: int,
        intensity: str = "moderate",
        calories_burned: int | None = None,
        distance_km: float | None = None,
        heart_rate_avg: int | None = None,
        heart_rate_max: int | None = None,
        notes: str = ""
    ) -> dict[str, Any]:
        """Log a physical activity."""
        # Estimate calories if not provided
        if calories_burned is None:
            met_values = {
                ActivityType.WALKING: 3.5,
                ActivityType.RUNNING: 8.0,
                ActivityType.CYCLING: 6.0,
                ActivityType.SWIMMING: 7.0,
                ActivityType.STRENGTH: 5.0,
                ActivityType.YOGA: 2.5,
                ActivityType.SPORTS: 6.0,
                ActivityType.HIKING: 5.5,
                ActivityType.OTHER: 4.0,
            }
            intensity_multiplier = {"low": 0.8, "moderate": 1.0, "vigorous": 1.3}
            met = met_values.get(activity_type, 4.0) * intensity_multiplier.get(intensity, 1.0)
            # Rough estimate: MET * weight(kg) * hours
            # Assume 70kg average if not available
            calories_burned = int(met * 70 * (duration_minutes / 60))

        record = ActivityRecord(
            activity_id=str(uuid4()),
            patient_id=patient_id,
            activity_type=activity_type,
            duration_minutes=duration_minutes,
            calories_burned=calories_burned,
            distance_km=distance_km,
            heart_rate_avg=heart_rate_avg,
            heart_rate_max=heart_rate_max,
            intensity=intensity,
            notes=notes,
        )

        if patient_id not in self._activities:
            self._activities[patient_id] = []
        self._activities[patient_id].append(record)

        # Update context
        context = self.get_health_context(patient_id)
        if context:
            context.wellness_data["last_activity"] = {
                "type": activity_type.value,
                "duration": duration_minutes,
                "timestamp": record.recorded_at.isoformat(),
            }

        # Check goal progress
        await self._check_exercise_goals(patient_id)

        # Publish event
        await self._publish_event(
            EventType.ACTIVITY_UPDATE,
            {
                "activity_type": activity_type.value,
                "duration_minutes": duration_minutes,
                "calories_burned": calories_burned,
            },
            patient_id=patient_id,
            tags=["activity", activity_type.value]
        )

        return {
            "activity_id": record.activity_id,
            "calories_burned": calories_burned,
            "duration_minutes": duration_minutes,
        }

    async def log_sleep(
        self,
        patient_id: str,
        sleep_start: datetime,
        sleep_end: datetime,
        quality: SleepQuality,
        deep_sleep_hours: float | None = None,
        rem_sleep_hours: float | None = None,
        awakenings: int = 0,
        notes: str = ""
    ) -> dict[str, Any]:
        """Log sleep data."""
        total_hours = (sleep_end - sleep_start).total_seconds() / 3600

        record = SleepRecord(
            sleep_id=str(uuid4()),
            patient_id=patient_id,
            sleep_start=sleep_start,
            sleep_end=sleep_end,
            total_hours=total_hours,
            deep_sleep_hours=deep_sleep_hours,
            rem_sleep_hours=rem_sleep_hours,
            awakenings=awakenings,
            quality=quality,
            notes=notes,
        )

        if patient_id not in self._sleep_records:
            self._sleep_records[patient_id] = []
        self._sleep_records[patient_id].append(record)

        # Update context
        context = self.get_health_context(patient_id)
        if context:
            context.wellness_data["last_sleep"] = {
                "hours": round(total_hours, 1),
                "quality": quality.name,
                "date": sleep_end.date().isoformat(),
            }

        # Analyze sleep quality
        analysis = self._analyze_sleep(record)

        # Check goals
        await self._check_sleep_goals(patient_id, total_hours)

        # Publish event
        await self._publish_event(
            EventType.SLEEP_DATA,
            {
                "total_hours": round(total_hours, 1),
                "quality": quality.value,
                "analysis": analysis,
            },
            patient_id=patient_id,
            tags=["sleep", quality.name.lower()]
        )

        return {
            "sleep_id": record.sleep_id,
            "total_hours": round(total_hours, 1),
            "analysis": analysis,
        }

    def _analyze_sleep(self, record: SleepRecord) -> dict[str, Any]:
        """Analyze sleep quality and patterns."""
        analysis = {
            "adequate_duration": record.total_hours >= 7,
            "quality_score": record.quality.value,
            "recommendations": [],
        }

        if record.total_hours < 6:
            analysis["recommendations"].append(
                "Consider getting more sleep - aim for 7-9 hours"
            )
        elif record.total_hours > 9:
            analysis["recommendations"].append(
                "You may be oversleeping - 7-9 hours is typically optimal"
            )

        if record.awakenings > 3:
            analysis["recommendations"].append(
                "Multiple awakenings detected - consider sleep environment improvements"
            )

        if record.quality.value <= 2:
            analysis["recommendations"].append(
                "Poor sleep quality - consider reviewing sleep hygiene practices"
            )

        return analysis

    async def log_nutrition(
        self,
        patient_id: str,
        meal_type: str,
        description: str = "",
        calories: int | None = None,
        protein_g: float | None = None,
        carbs_g: float | None = None,
        fat_g: float | None = None,
        fiber_g: float | None = None,
        water_ml: int = 0
    ) -> dict[str, Any]:
        """Log nutrition/meal data."""
        record = NutritionRecord(
            nutrition_id=str(uuid4()),
            patient_id=patient_id,
            meal_type=meal_type,
            calories=calories,
            protein_g=protein_g,
            carbs_g=carbs_g,
            fat_g=fat_g,
            fiber_g=fiber_g,
            water_ml=water_ml,
            description=description,
        )

        if patient_id not in self._nutrition_records:
            self._nutrition_records[patient_id] = []
        self._nutrition_records[patient_id].append(record)

        # Calculate daily totals
        today = datetime.utcnow().date()
        today_records = [
            r for r in self._nutrition_records[patient_id]
            if r.recorded_at.date() == today
        ]

        daily_calories = sum(r.calories or 0 for r in today_records)
        daily_water = sum(r.water_ml for r in today_records)

        # Publish event
        await self._publish_event(
            EventType.NUTRITION_LOG,
            {
                "meal_type": meal_type,
                "calories": calories,
                "daily_calories": daily_calories,
                "daily_water_ml": daily_water,
            },
            patient_id=patient_id,
            tags=["nutrition", meal_type]
        )

        return {
            "nutrition_id": record.nutrition_id,
            "daily_calories": daily_calories,
            "daily_water_ml": daily_water,
        }

    async def log_mood(
        self,
        patient_id: str,
        mood_level: MoodLevel,
        energy_level: int,
        stress_level: int,
        notes: str = "",
        factors: list[str] | None = None
    ) -> dict[str, Any]:
        """Log mood and mental wellness."""
        record = MoodRecord(
            mood_id=str(uuid4()),
            patient_id=patient_id,
            mood_level=mood_level,
            energy_level=min(10, max(1, energy_level)),
            stress_level=min(10, max(1, stress_level)),
            notes=notes,
            factors=factors or [],
        )

        if patient_id not in self._mood_records:
            self._mood_records[patient_id] = []
        self._mood_records[patient_id].append(record)

        # Update context
        context = self.get_health_context(patient_id)
        if context:
            context.wellness_data["mood"] = {
                "level": mood_level.name,
                "energy": energy_level,
                "stress": stress_level,
                "timestamp": record.recorded_at.isoformat(),
            }

        # Analyze mood trends
        analysis = self._analyze_mood_trends(patient_id)

        return {
            "mood_id": record.mood_id,
            "mood_trend": analysis,
        }

    def _analyze_mood_trends(self, patient_id: str) -> dict[str, Any]:
        """Analyze mood trends over recent period."""
        if patient_id not in self._mood_records:
            return {"trend": "insufficient_data"}

        recent = [
            r for r in self._mood_records[patient_id]
            if r.recorded_at > datetime.utcnow() - timedelta(days=7)
        ]

        if len(recent) < 3:
            return {"trend": "insufficient_data"}

        avg_mood = sum(r.mood_level.value for r in recent) / len(recent)
        avg_energy = sum(r.energy_level for r in recent) / len(recent)
        avg_stress = sum(r.stress_level for r in recent) / len(recent)

        return {
            "trend": "stable" if 2.5 <= avg_mood <= 3.5 else ("improving" if avg_mood > 3.5 else "declining"),
            "avg_mood": round(avg_mood, 1),
            "avg_energy": round(avg_energy, 1),
            "avg_stress": round(avg_stress, 1),
            "data_points": len(recent),
        }

    async def log_steps(
        self,
        patient_id: str,
        steps: int,
        date_str: str | None = None
    ) -> dict[str, Any]:
        """Log daily step count."""
        target_date = date_str or datetime.utcnow().date().isoformat()

        if patient_id not in self._daily_steps:
            self._daily_steps[patient_id] = {}

        # Add to existing count for the day
        current = self._daily_steps[patient_id].get(target_date, 0)
        self._daily_steps[patient_id][target_date] = current + steps

        total_steps = self._daily_steps[patient_id][target_date]

        # Check goals
        await self._check_step_goals(patient_id, total_steps)

        return {
            "date": target_date,
            "total_steps": total_steps,
            "goal_met": total_steps >= 10000,  # Default 10k goal
        }

    async def set_goal(
        self,
        patient_id: str,
        goal_type: str,
        target_value: float,
        unit: str,
        end_date: date | None = None
    ) -> dict[str, Any]:
        """Set a wellness goal."""
        goal = WellnessGoal(
            goal_id=str(uuid4()),
            patient_id=patient_id,
            goal_type=goal_type,
            target_value=target_value,
            current_value=0,
            unit=unit,
            start_date=date.today(),
            end_date=end_date,
        )

        if patient_id not in self._goals:
            self._goals[patient_id] = {}

        self._goals[patient_id][goal.goal_id] = goal

        return {
            "goal_id": goal.goal_id,
            "goal_type": goal_type,
            "target": target_value,
            "unit": unit,
        }

    async def _check_step_goals(self, patient_id: str, steps: int) -> None:
        """Check progress towards step goals."""
        if patient_id not in self._goals:
            return

        for goal in self._goals[patient_id].values():
            if goal.goal_type == "steps" and goal.is_active:
                goal.current_value = steps
                if steps >= goal.target_value:
                    await self._publish_event(
                        EventType.WELLNESS_GOAL_PROGRESS,
                        {"goal_type": "steps", "achieved": True, "value": steps},
                        patient_id=patient_id,
                        tags=["goal", "achieved"]
                    )

    async def _check_sleep_goals(self, patient_id: str, hours: float) -> None:
        """Check progress towards sleep goals."""
        if patient_id not in self._goals:
            return

        for goal in self._goals[patient_id].values():
            if goal.goal_type == "sleep" and goal.is_active:
                goal.current_value = hours
                if hours >= goal.target_value:
                    await self._publish_event(
                        EventType.WELLNESS_GOAL_PROGRESS,
                        {"goal_type": "sleep", "achieved": True, "hours": hours},
                        patient_id=patient_id,
                        tags=["goal", "achieved"]
                    )

    async def _check_exercise_goals(self, patient_id: str) -> None:
        """Check progress towards exercise goals."""
        if patient_id not in self._goals:
            return

        # Calculate weekly exercise minutes
        week_ago = datetime.utcnow() - timedelta(days=7)
        activities = self._activities.get(patient_id, [])
        weekly_minutes = sum(
            a.duration_minutes for a in activities
            if a.recorded_at > week_ago
        )

        for goal in self._goals[patient_id].values():
            if goal.goal_type == "exercise" and goal.is_active:
                goal.current_value = weekly_minutes
                if weekly_minutes >= goal.target_value:
                    await self._publish_event(
                        EventType.WELLNESS_GOAL_PROGRESS,
                        {"goal_type": "exercise", "achieved": True, "minutes": weekly_minutes},
                        patient_id=patient_id,
                        tags=["goal", "achieved"]
                    )

    def get_daily_summary(self, patient_id: str, target_date: date | None = None) -> dict[str, Any]:
        """Get daily wellness summary."""
        target = target_date or date.today()
        target_str = target.isoformat()

        # Steps
        steps = self._daily_steps.get(patient_id, {}).get(target_str, 0)

        # Activities
        activities = [
            a for a in self._activities.get(patient_id, [])
            if a.recorded_at.date() == target
        ]
        exercise_minutes = sum(a.duration_minutes for a in activities)
        calories_burned = sum(a.calories_burned or 0 for a in activities)

        # Sleep (from previous night)
        sleep_records = [
            s for s in self._sleep_records.get(patient_id, [])
            if s.sleep_end.date() == target
        ]
        sleep_hours = sleep_records[0].total_hours if sleep_records else None

        # Nutrition
        nutrition = [
            n for n in self._nutrition_records.get(patient_id, [])
            if n.recorded_at.date() == target
        ]
        calories_consumed = sum(n.calories or 0 for n in nutrition)
        water_ml = sum(n.water_ml for n in nutrition)

        # Mood
        mood_records = [
            m for m in self._mood_records.get(patient_id, [])
            if m.recorded_at.date() == target
        ]
        latest_mood = mood_records[-1] if mood_records else None

        return {
            "date": target_str,
            "steps": steps,
            "exercise_minutes": exercise_minutes,
            "calories_burned": calories_burned,
            "sleep_hours": round(sleep_hours, 1) if sleep_hours else None,
            "calories_consumed": calories_consumed,
            "water_ml": water_ml,
            "mood": latest_mood.mood_level.name if latest_mood else None,
            "energy": latest_mood.energy_level if latest_mood else None,
            "stress": latest_mood.stress_level if latest_mood else None,
        }

    def get_weekly_summary(self, patient_id: str) -> dict[str, Any]:
        """Get weekly wellness summary."""
        today = date.today()
        week_ago = today - timedelta(days=7)

        # Aggregate data
        total_steps = sum(
            steps for d, steps in self._daily_steps.get(patient_id, {}).items()
            if date.fromisoformat(d) > week_ago
        )

        activities = [
            a for a in self._activities.get(patient_id, [])
            if a.recorded_at.date() > week_ago
        ]
        total_exercise = sum(a.duration_minutes for a in activities)
        total_calories_burned = sum(a.calories_burned or 0 for a in activities)

        sleep_records = [
            s for s in self._sleep_records.get(patient_id, [])
            if s.sleep_end.date() > week_ago
        ]
        avg_sleep = (
            sum(s.total_hours for s in sleep_records) / len(sleep_records)
            if sleep_records else None
        )

        mood_records = [
            m for m in self._mood_records.get(patient_id, [])
            if m.recorded_at.date() > week_ago
        ]
        avg_mood = (
            sum(m.mood_level.value for m in mood_records) / len(mood_records)
            if mood_records else None
        )

        # Goals progress
        goals_progress = []
        for goal in self._goals.get(patient_id, {}).values():
            if goal.is_active:
                progress = (goal.current_value / goal.target_value * 100) if goal.target_value > 0 else 0
                goals_progress.append({
                    "type": goal.goal_type,
                    "target": goal.target_value,
                    "current": goal.current_value,
                    "progress_percent": min(100, round(progress, 1)),
                })

        return {
            "period": f"{week_ago.isoformat()} to {today.isoformat()}",
            "total_steps": total_steps,
            "avg_daily_steps": total_steps // 7,
            "total_exercise_minutes": total_exercise,
            "total_calories_burned": total_calories_burned,
            "avg_sleep_hours": round(avg_sleep, 1) if avg_sleep else None,
            "avg_mood": round(avg_mood, 1) if avg_mood else None,
            "workout_days": len(set(a.recorded_at.date() for a in activities)),
            "goals": goals_progress,
        }

    def get_recommendations(self, patient_id: str) -> list[dict[str, Any]]:
        """Generate personalized wellness recommendations."""
        recommendations = []

        # Get recent data
        summary = self.get_weekly_summary(patient_id)

        # Step recommendations
        avg_steps = summary.get("avg_daily_steps", 0)
        if avg_steps < 5000:
            recommendations.append({
                "category": "activity",
                "priority": "high",
                "recommendation": "Try to increase daily steps - aim for at least 7,500 steps per day",
                "current": f"{avg_steps} avg daily steps",
            })
        elif avg_steps < 7500:
            recommendations.append({
                "category": "activity",
                "priority": "medium",
                "recommendation": "You're doing well! Push for 10,000 steps for optimal health",
                "current": f"{avg_steps} avg daily steps",
            })

        # Exercise recommendations
        workout_days = summary.get("workout_days", 0)
        if workout_days < 3:
            recommendations.append({
                "category": "exercise",
                "priority": "high",
                "recommendation": "Aim for at least 3-4 workout sessions per week",
                "current": f"{workout_days} workout days this week",
            })

        # Sleep recommendations
        avg_sleep = summary.get("avg_sleep_hours")
        if avg_sleep and avg_sleep < 7:
            recommendations.append({
                "category": "sleep",
                "priority": "high",
                "recommendation": "Prioritize sleep - aim for 7-9 hours per night",
                "current": f"{avg_sleep} hours average",
            })

        # Mood recommendations
        avg_mood = summary.get("avg_mood")
        if avg_mood and avg_mood < 3:
            recommendations.append({
                "category": "mental_health",
                "priority": "medium",
                "recommendation": "Consider stress-reduction activities like meditation or yoga",
                "current": f"Mood score: {avg_mood}/5",
            })

        if not recommendations:
            recommendations.append({
                "category": "general",
                "priority": "low",
                "recommendation": "Great job maintaining your wellness routine! Keep it up!",
                "current": "Meeting goals",
            })

        return recommendations

    # Message handlers

    async def _handle_log_activity(self, message: Message) -> Message:
        """Handle log activity request."""
        content = message.content
        try:
            result = await self.log_activity(
                patient_id=content["patient_id"],
                activity_type=ActivityType(content["activity_type"]),
                duration_minutes=content["duration_minutes"],
                intensity=content.get("intensity", "moderate"),
                calories_burned=content.get("calories_burned"),
                distance_km=content.get("distance_km"),
                heart_rate_avg=content.get("heart_rate_avg"),
                heart_rate_max=content.get("heart_rate_max"),
                notes=content.get("notes", ""),
            )
            return message.create_response(self.agent_id, {"success": True, **result})
        except Exception as e:
            return message.create_response(self.agent_id, {"success": False, "error": str(e)})

    async def _handle_log_sleep(self, message: Message) -> Message:
        """Handle log sleep request."""
        content = message.content
        try:
            result = await self.log_sleep(
                patient_id=content["patient_id"],
                sleep_start=datetime.fromisoformat(content["sleep_start"]),
                sleep_end=datetime.fromisoformat(content["sleep_end"]),
                quality=SleepQuality(content["quality"]),
                deep_sleep_hours=content.get("deep_sleep_hours"),
                rem_sleep_hours=content.get("rem_sleep_hours"),
                awakenings=content.get("awakenings", 0),
                notes=content.get("notes", ""),
            )
            return message.create_response(self.agent_id, {"success": True, **result})
        except Exception as e:
            return message.create_response(self.agent_id, {"success": False, "error": str(e)})

    async def _handle_log_nutrition(self, message: Message) -> Message:
        """Handle log nutrition request."""
        content = message.content
        try:
            result = await self.log_nutrition(
                patient_id=content["patient_id"],
                meal_type=content["meal_type"],
                description=content.get("description", ""),
                calories=content.get("calories"),
                protein_g=content.get("protein_g"),
                carbs_g=content.get("carbs_g"),
                fat_g=content.get("fat_g"),
                fiber_g=content.get("fiber_g"),
                water_ml=content.get("water_ml", 0),
            )
            return message.create_response(self.agent_id, {"success": True, **result})
        except Exception as e:
            return message.create_response(self.agent_id, {"success": False, "error": str(e)})

    async def _handle_log_mood(self, message: Message) -> Message:
        """Handle log mood request."""
        content = message.content
        try:
            result = await self.log_mood(
                patient_id=content["patient_id"],
                mood_level=MoodLevel(content["mood_level"]),
                energy_level=content["energy_level"],
                stress_level=content["stress_level"],
                notes=content.get("notes", ""),
                factors=content.get("factors"),
            )
            return message.create_response(self.agent_id, {"success": True, **result})
        except Exception as e:
            return message.create_response(self.agent_id, {"success": False, "error": str(e)})

    async def _handle_log_steps(self, message: Message) -> Message:
        """Handle log steps request."""
        content = message.content
        try:
            result = await self.log_steps(
                patient_id=content["patient_id"],
                steps=content["steps"],
                date_str=content.get("date"),
            )
            return message.create_response(self.agent_id, {"success": True, **result})
        except Exception as e:
            return message.create_response(self.agent_id, {"success": False, "error": str(e)})

    async def _handle_set_goal(self, message: Message) -> Message:
        """Handle set goal request."""
        content = message.content
        try:
            result = await self.set_goal(
                patient_id=content["patient_id"],
                goal_type=content["goal_type"],
                target_value=content["target_value"],
                unit=content["unit"],
                end_date=date.fromisoformat(content["end_date"]) if content.get("end_date") else None,
            )
            return message.create_response(self.agent_id, {"success": True, **result})
        except Exception as e:
            return message.create_response(self.agent_id, {"success": False, "error": str(e)})

    async def _handle_get_goals(self, message: Message) -> Message:
        """Handle get goals request."""
        patient_id = message.content.get("patient_id")
        goals = []

        for goal in self._goals.get(patient_id, {}).values():
            if goal.is_active:
                progress = (goal.current_value / goal.target_value * 100) if goal.target_value > 0 else 0
                goals.append({
                    "goal_id": goal.goal_id,
                    "type": goal.goal_type,
                    "target": goal.target_value,
                    "current": goal.current_value,
                    "unit": goal.unit,
                    "progress_percent": min(100, round(progress, 1)),
                })

        return message.create_response(self.agent_id, {"success": True, "goals": goals})

    async def _handle_get_daily_summary(self, message: Message) -> Message:
        """Handle get daily summary request."""
        content = message.content
        patient_id = content.get("patient_id")
        target_date = date.fromisoformat(content["date"]) if content.get("date") else None

        summary = self.get_daily_summary(patient_id, target_date)
        return message.create_response(self.agent_id, {"success": True, **summary})

    async def _handle_get_weekly_summary(self, message: Message) -> Message:
        """Handle get weekly summary request."""
        patient_id = message.content.get("patient_id")
        summary = self.get_weekly_summary(patient_id)
        return message.create_response(self.agent_id, {"success": True, **summary})

    async def _handle_get_recommendations(self, message: Message) -> Message:
        """Handle get recommendations request."""
        patient_id = message.content.get("patient_id")
        recommendations = self.get_recommendations(patient_id)
        return message.create_response(
            self.agent_id,
            {"success": True, "recommendations": recommendations}
        )
