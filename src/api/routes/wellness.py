"""Wellness tracking routes."""

from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ...agents.wellness_agent import ActivityType, MoodLevel, SleepQuality
from ..dependencies import get_health_system, HealthMonitoringSystem

router = APIRouter()


class LogActivityRequest(BaseModel):
    """Request to log an activity."""

    patient_id: str
    activity_type: str
    duration_minutes: int = Field(..., gt=0)
    intensity: str = "moderate"
    calories_burned: int | None = None
    distance_km: float | None = None
    heart_rate_avg: int | None = None
    heart_rate_max: int | None = None
    notes: str | None = None


class LogSleepRequest(BaseModel):
    """Request to log sleep."""

    patient_id: str
    sleep_start: datetime
    sleep_end: datetime
    quality: int = Field(..., ge=1, le=4, description="1=Poor, 2=Fair, 3=Good, 4=Excellent")
    deep_sleep_hours: float | None = None
    rem_sleep_hours: float | None = None
    awakenings: int = 0
    notes: str | None = None


class LogNutritionRequest(BaseModel):
    """Request to log nutrition."""

    patient_id: str
    meal_type: str
    description: str | None = None
    calories: int | None = None
    protein_g: float | None = None
    carbs_g: float | None = None
    fat_g: float | None = None
    fiber_g: float | None = None
    water_ml: int = 0


class LogMoodRequest(BaseModel):
    """Request to log mood."""

    patient_id: str
    mood_level: int = Field(..., ge=1, le=5)
    energy_level: int = Field(..., ge=1, le=10)
    stress_level: int = Field(..., ge=1, le=10)
    notes: str | None = None
    factors: list[str] = Field(default_factory=list)


class LogStepsRequest(BaseModel):
    """Request to log steps."""

    patient_id: str
    steps: int = Field(..., gt=0)
    date: str | None = None


class SetGoalRequest(BaseModel):
    """Request to set a goal."""

    patient_id: str
    goal_type: str
    target_value: float
    unit: str
    end_date: date | None = None


@router.post("/activity", response_model=dict[str, Any])
async def log_activity(
    data: LogActivityRequest,
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Log a physical activity."""
    if not health_system.wellness_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wellness agent not available"
        )

    try:
        activity_type = ActivityType(data.activity_type)
    except ValueError:
        activity_type = ActivityType.OTHER

    result = await health_system.wellness_agent.log_activity(
        patient_id=data.patient_id,
        activity_type=activity_type,
        duration_minutes=data.duration_minutes,
        intensity=data.intensity,
        calories_burned=data.calories_burned,
        distance_km=data.distance_km,
        heart_rate_avg=data.heart_rate_avg,
        heart_rate_max=data.heart_rate_max,
        notes=data.notes or "",
    )

    return {
        "message": "Activity logged successfully",
        **result,
    }


@router.post("/sleep", response_model=dict[str, Any])
async def log_sleep(
    data: LogSleepRequest,
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Log sleep data."""
    if not health_system.wellness_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wellness agent not available"
        )

    result = await health_system.wellness_agent.log_sleep(
        patient_id=data.patient_id,
        sleep_start=data.sleep_start,
        sleep_end=data.sleep_end,
        quality=SleepQuality(data.quality),
        deep_sleep_hours=data.deep_sleep_hours,
        rem_sleep_hours=data.rem_sleep_hours,
        awakenings=data.awakenings,
        notes=data.notes or "",
    )

    return {
        "message": "Sleep data logged successfully",
        **result,
    }


@router.post("/nutrition", response_model=dict[str, Any])
async def log_nutrition(
    data: LogNutritionRequest,
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Log nutrition/meal data."""
    if not health_system.wellness_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wellness agent not available"
        )

    result = await health_system.wellness_agent.log_nutrition(
        patient_id=data.patient_id,
        meal_type=data.meal_type,
        description=data.description or "",
        calories=data.calories,
        protein_g=data.protein_g,
        carbs_g=data.carbs_g,
        fat_g=data.fat_g,
        fiber_g=data.fiber_g,
        water_ml=data.water_ml,
    )

    return {
        "message": "Nutrition logged successfully",
        **result,
    }


@router.post("/mood", response_model=dict[str, Any])
async def log_mood(
    data: LogMoodRequest,
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Log mood and mental wellness."""
    if not health_system.wellness_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wellness agent not available"
        )

    result = await health_system.wellness_agent.log_mood(
        patient_id=data.patient_id,
        mood_level=MoodLevel(data.mood_level),
        energy_level=data.energy_level,
        stress_level=data.stress_level,
        notes=data.notes or "",
        factors=data.factors,
    )

    return {
        "message": "Mood logged successfully",
        **result,
    }


@router.post("/steps", response_model=dict[str, Any])
async def log_steps(
    data: LogStepsRequest,
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Log daily step count."""
    if not health_system.wellness_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wellness agent not available"
        )

    result = await health_system.wellness_agent.log_steps(
        patient_id=data.patient_id,
        steps=data.steps,
        date_str=data.date,
    )

    return {
        "message": "Steps logged successfully",
        **result,
    }


@router.post("/goals", response_model=dict[str, Any])
async def set_goal(
    data: SetGoalRequest,
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Set a wellness goal."""
    if not health_system.wellness_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wellness agent not available"
        )

    result = await health_system.wellness_agent.set_goal(
        patient_id=data.patient_id,
        goal_type=data.goal_type,
        target_value=data.target_value,
        unit=data.unit,
        end_date=data.end_date,
    )

    return {
        "message": "Goal set successfully",
        **result,
    }


@router.get("/{patient_id}/goals", response_model=dict[str, Any])
async def get_goals(
    patient_id: str,
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Get wellness goals for a patient."""
    if not health_system.wellness_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wellness agent not available"
        )

    goals = []
    for goal in health_system.wellness_agent._goals.get(patient_id, {}).values():
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

    return {
        "patient_id": patient_id,
        "goals": goals,
    }


@router.get("/{patient_id}/daily", response_model=dict[str, Any])
async def get_daily_summary(
    patient_id: str,
    target_date: str | None = None,
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Get daily wellness summary."""
    if not health_system.wellness_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wellness agent not available"
        )

    date_obj = date.fromisoformat(target_date) if target_date else None
    summary = health_system.wellness_agent.get_daily_summary(patient_id, date_obj)

    return summary


@router.get("/{patient_id}/weekly", response_model=dict[str, Any])
async def get_weekly_summary(
    patient_id: str,
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Get weekly wellness summary."""
    if not health_system.wellness_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wellness agent not available"
        )

    summary = health_system.wellness_agent.get_weekly_summary(patient_id)

    return summary


@router.get("/{patient_id}/recommendations", response_model=dict[str, Any])
async def get_wellness_recommendations(
    patient_id: str,
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Get personalized wellness recommendations."""
    if not health_system.wellness_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Wellness agent not available"
        )

    recommendations = health_system.wellness_agent.get_recommendations(patient_id)

    return {
        "patient_id": patient_id,
        "recommendations": recommendations,
    }
