"""Configuration settings for the Health Monitoring Platform."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DatabaseSettings:
    """Database configuration."""

    path: str = "health_monitor.db"
    echo: bool = False


@dataclass
class AgentSettings:
    """Agent system configuration."""

    # Event bus settings
    event_queue_size: int = 10000
    event_history_size: int = 1000

    # Agent health check interval (seconds)
    health_check_interval: int = 5

    # Message TTL (seconds)
    default_message_ttl: int = 300


@dataclass
class AlertSettings:
    """Alert configuration."""

    # Escalation timeouts (minutes)
    critical_escalation_minutes: int = 5
    urgent_escalation_minutes: int = 15
    warning_escalation_minutes: int = 60

    # Notification settings
    enable_push_notifications: bool = True
    enable_sms_notifications: bool = False
    enable_email_notifications: bool = True


@dataclass
class VitalSettings:
    """Vital signs monitoring configuration."""

    # History retention
    max_readings_per_vital: int = 1000

    # Trend analysis window (hours)
    default_trend_window_hours: int = 24

    # Anomaly detection sensitivity
    anomaly_threshold_multiplier: float = 1.5


@dataclass
class WellnessSettings:
    """Wellness tracking configuration."""

    # Default goals
    default_step_goal: int = 10000
    default_sleep_goal_hours: float = 8.0
    default_water_goal_ml: int = 2500

    # Activity calorie multipliers
    activity_met_values: dict = None

    def __post_init__(self):
        if self.activity_met_values is None:
            self.activity_met_values = {
                "walking": 3.5,
                "running": 8.0,
                "cycling": 6.0,
                "swimming": 7.0,
                "strength": 5.0,
                "yoga": 2.5,
            }


@dataclass
class APISettings:
    """API configuration."""

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    cors_origins: list = None

    def __post_init__(self):
        if self.cors_origins is None:
            self.cors_origins = ["*"]


@dataclass
class Settings:
    """Main settings container."""

    app_name: str = "Health Monitoring Platform"
    version: str = "1.0.0"
    environment: str = "development"

    database: DatabaseSettings = None
    agents: AgentSettings = None
    alerts: AlertSettings = None
    vitals: VitalSettings = None
    wellness: WellnessSettings = None
    api: APISettings = None

    def __post_init__(self):
        self.database = self.database or DatabaseSettings()
        self.agents = self.agents or AgentSettings()
        self.alerts = self.alerts or AlertSettings()
        self.vitals = self.vitals or VitalSettings()
        self.wellness = self.wellness or WellnessSettings()
        self.api = self.api or APISettings()


def load_settings() -> Settings:
    """Load settings from environment or defaults."""
    return Settings(
        environment=os.getenv("ENVIRONMENT", "development"),
        database=DatabaseSettings(
            path=os.getenv("DATABASE_PATH", "health_monitor.db"),
        ),
        api=APISettings(
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8000")),
            debug=os.getenv("DEBUG", "true").lower() == "true",
        ),
    )


# Global settings instance
settings = load_settings()
