"""Dashboard and overview routes."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from ..dependencies import get_health_system, HealthMonitoringSystem

router = APIRouter()


@router.get("/{patient_id}", response_model=dict[str, Any])
async def get_patient_dashboard(
    patient_id: str,
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """
    Get comprehensive dashboard data for a patient.

    Returns unified health data from all agents including:
    - Overall health status
    - Recent vital readings
    - Active alerts
    - Upcoming medications
    - Wellness summary
    - Recommendations
    """
    if not health_system.coordinator_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Coordinator agent not available"
        )

    dashboard = health_system.coordinator_agent.get_dashboard_data(patient_id)

    if "error" in dashboard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=dashboard["error"]
        )

    return dashboard


@router.get("/{patient_id}/summary", response_model=dict[str, Any])
async def get_health_summary(
    patient_id: str,
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """
    Get comprehensive health summary for a patient.

    Aggregates data from all agents to provide a unified health assessment.
    """
    if not health_system.coordinator_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Coordinator agent not available"
        )

    try:
        summary = await health_system.coordinator_agent.generate_health_summary(patient_id)

        return {
            "patient_id": patient_id,
            "overall_status": summary.overall_status,
            "risk_level": summary.risk_level.value,
            "wellness_score": summary.wellness_score,
            "vitals_status": summary.vitals_status,
            "medication_adherence": summary.medication_adherence,
            "active_symptoms": summary.active_symptoms,
            "active_alerts": summary.active_alerts,
            "insights": summary.insights,
            "recommendations": summary.recommendations,
            "action_items": summary.action_items,
            "generated_at": summary.generated_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/{patient_id}/risk", response_model=dict[str, Any])
async def get_risk_assessment(
    patient_id: str,
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Get comprehensive risk assessment for a patient."""
    if not health_system.coordinator_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Coordinator agent not available"
        )

    context = health_system.coordinator_agent.get_health_context(patient_id)

    if not context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )

    overall_risk = health_system.coordinator_agent._calculate_overall_risk(context)

    return {
        "patient_id": patient_id,
        "overall_risk": overall_risk.value,
        "risk_factors": {k: v.value for k, v in context.risk_levels.items()},
        "active_alerts": len(context.active_alerts),
        "active_symptoms": len(context.active_symptoms),
    }


@router.get("/{patient_id}/insights", response_model=dict[str, Any])
async def get_health_insights(
    patient_id: str,
    limit: int = 20,
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Get health insights collected from all agents."""
    if not health_system.coordinator_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Coordinator agent not available"
        )

    insights = health_system.coordinator_agent._collected_insights.get(
        patient_id, []
    )[-limit:]

    return {
        "patient_id": patient_id,
        "insights": insights,
        "count": len(insights),
    }


@router.get("/{patient_id}/recommendations", response_model=dict[str, Any])
async def get_health_recommendations(
    patient_id: str,
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Get personalized health recommendations."""
    if not health_system.coordinator_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Coordinator agent not available"
        )

    context = health_system.coordinator_agent.get_health_context(patient_id)

    if not context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )

    overall_risk = health_system.coordinator_agent._calculate_overall_risk(context)
    recommendations = health_system.coordinator_agent._generate_recommendations(
        context, overall_risk
    )

    return {
        "patient_id": patient_id,
        "recommendations": recommendations,
    }


@router.get("/system/status", response_model=dict[str, Any])
async def get_system_status(
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Get health monitoring system status."""
    return health_system.get_system_status()


@router.get("/system/agents", response_model=dict[str, Any])
async def get_agent_status(
    health_system: HealthMonitoringSystem = Depends(get_health_system),
) -> dict[str, Any]:
    """Get status of all agents."""
    status_info = health_system.get_system_status()

    return {
        "agents": status_info.get("agents", {}),
        "capabilities": status_info.get("capabilities", {}),
    }
