"""Alert Analyzer Tool — Parses and classifies incoming alert data."""

import json


def analyze_alert(alert_json: str) -> dict:
    """Parses raw alert JSON and extracts key fields for analysis.

    Args:
        alert_json: A JSON string containing alert data with fields like
            alert_type, resource, severity, metric_name, metric_value, etc.

    Returns:
        A dictionary with the parsed alert summary and risk assessment.
    """
    try:
        alert = json.loads(alert_json) if isinstance(alert_json, str) else alert_json
    except json.JSONDecodeError:
        return {
            "status": "error",
            "message": "Failed to parse alert JSON. Please provide valid JSON.",
        }

    # Extract key fields with defaults
    alert_id = alert.get("alert_id", "unknown")
    alert_type = alert.get("alert_type", "unknown")
    resource = alert.get("resource", "unknown")
    severity = alert.get("severity", "unknown").lower()
    metric_name = alert.get("metric_name", "")
    metric_value = alert.get("metric_value", 0)
    threshold = alert.get("threshold", 0)
    description = alert.get("description", "")
    labels = alert.get("labels", {})

    # Compute basic risk indicators
    severity_score = {
        "critical": 4,
        "high": 3,
        "medium": 2,
        "low": 1,
        "info": 0,
    }.get(severity, 2)

    threshold_breach_pct = 0.0
    if threshold > 0:
        threshold_breach_pct = round(((metric_value - threshold) / threshold) * 100, 2)

    risk_level = "low"
    if severity_score >= 4 or threshold_breach_pct > 50:
        risk_level = "high"
    elif severity_score >= 3 or threshold_breach_pct > 20:
        risk_level = "medium"

    return {
        "status": "success",
        "alert_id": alert_id,
        "alert_type": alert_type,
        "resource": resource,
        "severity": severity,
        "severity_score": severity_score,
        "metric_name": metric_name,
        "metric_value": metric_value,
        "threshold": threshold,
        "threshold_breach_percentage": threshold_breach_pct,
        "description": description,
        "labels": labels,
        "initial_risk_level": risk_level,
        "summary": (
            f"Alert '{alert_type}' on resource '{resource}' with severity "
            f"'{severity}'. Metric '{metric_name}' at {metric_value} "
            f"(threshold: {threshold}, breach: {threshold_breach_pct}%). "
            f"Initial risk assessment: {risk_level}."
        ),
    }
