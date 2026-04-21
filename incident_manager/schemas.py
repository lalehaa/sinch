"""Data models for the Incident Manager AI Assistant."""

from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class AlertData:
    """Represents an incoming alert from a monitoring system."""
    alert_id: str
    alert_type: str
    resource: str
    severity: str
    metric_name: str = ""
    metric_value: float = 0.0
    threshold: float = 0.0
    description: str = ""
    timestamp: str = ""
    labels: dict = field(default_factory=dict)

    def to_summary(self) -> str:
        """Returns a human-readable summary of the alert."""
        return (
            f"Alert [{self.alert_id}]: {self.alert_type} on {self.resource} "
            f"(severity={self.severity}, metric={self.metric_name}={self.metric_value}, "
            f"threshold={self.threshold})"
        )


@dataclass
class IncidentRecord:
    """Represents a historical incident from the database."""
    incident_id: str
    alert_type: str
    resource: str
    severity: str
    timestamp: str
    resolution: str  # "critical_confirmed", "false_positive", "auto_resolved"
    root_cause: str = ""
    action_taken: str = ""
    time_to_resolve_minutes: int = 0


@dataclass
class LogEntry:
    """Represents a log entry from Cloud Logging."""
    timestamp: str
    severity: str  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    resource: str
    message: str
    labels: dict = field(default_factory=dict)


@dataclass
class PatternMatch:
    """Result of pattern matching against historical data."""
    pattern_found: bool
    confidence_score: float  # 0.0 to 1.0
    matching_incidents: list = field(default_factory=list)
    pattern_description: str = ""
    recommendation: str = ""  # "critical", "false_positive", "needs_investigation"


@dataclass
class AgentVerdict:
    """Final verdict from the agent."""
    alert_id: str
    verdict: str  # "critical", "false_positive", "needs_investigation"
    confidence: float
    reasoning: str
    pattern_found: bool
    matching_incident_ids: list = field(default_factory=list)
    recommended_action: str = ""
