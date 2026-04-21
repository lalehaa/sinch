"""Pattern Matcher Tool — Compares alerts against historical patterns."""

import json


def check_pattern(alert_data: str, historical_data: str) -> dict:
    """Compares the current alert against historical incident patterns.

    Analyzes the current alert in the context of historical incidents
    and log data to determine if there is a matching known pattern.

    Args:
        alert_data: JSON string with current alert analysis, including fields
            like alert_type, resource, severity, error_pattern, etc.
        historical_data: JSON string with historical incident lookup results,
            including past incidents and their resolutions.

    Returns:
        A dictionary with pattern matching results, confidence score,
        and recommendation.
    """
    try:
        alert = json.loads(alert_data) if isinstance(alert_data, str) else alert_data
        history = (
            json.loads(historical_data)
            if isinstance(historical_data, str)
            else historical_data
        )
    except json.JSONDecodeError:
        return {
            "status": "error",
            "message": "Failed to parse input JSON data.",
        }

    # Extract key metrics from alert
    alert_type = alert.get("alert_type", "unknown")
    severity = alert.get("severity", "unknown")
    risk_level = alert.get("initial_risk_level", "unknown")
    has_errors = alert.get("has_errors", False)
    error_pattern = alert.get("error_pattern", "none")
    threshold_breach_pct = alert.get("threshold_breach_percentage", 0)

    # Extract historical analysis
    total_matches = history.get("total_matches", 0)
    analysis = history.get("analysis", {})
    critical_rate = analysis.get("critical_rate_pct", 0)
    false_positive_count = analysis.get("false_positive_count", 0)
    critical_count = analysis.get("critical_confirmed_count", 0)
    matching_incidents = history.get("matching_incidents", [])

    # --- Pattern Matching Logic ---

    confidence_score = 0.5  # Start neutral
    signals = []

    # Signal 1: Historical pattern strength
    if total_matches > 0:
        if critical_rate >= 75:
            confidence_score += 0.25
            signals.append(
                f"Strong critical history: {critical_rate}% of similar "
                f"alerts were confirmed critical"
            )
        elif critical_rate <= 25:
            confidence_score -= 0.25
            signals.append(
                f"Strong false-positive history: {100 - critical_rate}% of "
                f"similar alerts were false positives"
            )
        else:
            signals.append(
                f"Mixed history: {critical_rate}% critical rate across "
                f"{total_matches} incidents"
            )
    else:
        signals.append("No historical matches found — this is a novel alert type/resource combination")

    # Signal 2: Severity
    severity_lower = severity.lower() if isinstance(severity, str) else "unknown"
    if severity_lower in ("critical", "high"):
        confidence_score += 0.1
        signals.append(f"High severity alert ({severity})")
    elif severity_lower in ("low", "info"):
        confidence_score -= 0.1
        signals.append(f"Low severity alert ({severity})")

    # Signal 3: Error logs correlation
    if has_errors:
        if error_pattern in ("critical_errors_present", "error_spike"):
            confidence_score += 0.2
            signals.append(
                f"Correlated error logs detected: {error_pattern}"
            )
        else:
            confidence_score += 0.05
            signals.append("Some error logs present but no spike pattern")
    else:
        confidence_score -= 0.15
        signals.append("No error logs found — reduces likelihood of real incident")

    # Signal 4: Threshold breach severity
    if threshold_breach_pct > 50:
        confidence_score += 0.15
        signals.append(
            f"Severe threshold breach: {threshold_breach_pct}% above threshold"
        )
    elif threshold_breach_pct > 20:
        confidence_score += 0.05
        signals.append(
            f"Moderate threshold breach: {threshold_breach_pct}% above threshold"
        )
    elif threshold_breach_pct <= 5:
        confidence_score -= 0.1
        signals.append(
            f"Marginal threshold breach: only {threshold_breach_pct}% above threshold"
        )

    # Clamp confidence (positive = more likely critical)
    confidence_score = max(0.0, min(1.0, confidence_score))

    # Determine recommendation
    pattern_found = total_matches > 0
    if confidence_score >= 0.7:
        recommendation = "critical"
        recommendation_text = (
            "HIGH CONFIDENCE — This alert matches a pattern of confirmed "
            "critical incidents. Immediate investigation recommended."
        )
    elif confidence_score <= 0.3:
        recommendation = "false_positive"
        recommendation_text = (
            "HIGH CONFIDENCE — This alert matches a pattern of known false "
            "positives. Consider suppressing or adjusting the alert threshold."
        )
    else:
        recommendation = "needs_investigation"
        recommendation_text = (
            "INCONCLUSIVE — The pattern analysis is not definitive. "
            "Manual investigation is recommended to confirm or dismiss."
        )

    # Collect matching incident IDs
    matching_ids = [inc.get("incident_id", "unknown") for inc in matching_incidents]

    return {
        "status": "success",
        "pattern_found": pattern_found,
        "confidence_score": round(confidence_score, 2),
        "recommendation": recommendation,
        "recommendation_text": recommendation_text,
        "signals": signals,
        "matching_incident_ids": matching_ids,
        "summary": (
            f"Pattern {'found' if pattern_found else 'not found'}. "
            f"Confidence: {round(confidence_score * 100)}%. "
            f"Recommendation: {recommendation.upper()}. "
            f"Signals: {'; '.join(signals)}"
        ),
    }
