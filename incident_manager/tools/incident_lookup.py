"""Incident Lookup Tool — Searches historical incident database.

V1 uses in-memory mock data simulating a BigQuery historical incidents table.
For production, replace with google-cloud-bigquery client.
"""


# --- Mock Historical Incidents Database ---
# Simulates a BigQuery table with past incidents and their resolutions

_HISTORICAL_INCIDENTS = [
    {
        "incident_id": "INC-2024-001",
        "alert_type": "high_cpu",
        "resource": "prod-server-01",
        "severity": "critical",
        "timestamp": "2024-11-15T08:30:00Z",
        "resolution": "critical_confirmed",
        "root_cause": "Memory leak in v2.12.0 causing excessive GC cycles",
        "action_taken": "Rolled back to v2.11.9, patched in v2.12.1",
        "time_to_resolve_minutes": 45,
    },
    {
        "incident_id": "INC-2024-002",
        "alert_type": "high_cpu",
        "resource": "prod-server-01",
        "severity": "high",
        "timestamp": "2024-12-01T14:15:00Z",
        "resolution": "false_positive",
        "root_cause": "Scheduled batch job caused temporary CPU spike",
        "action_taken": "Adjusted alert threshold for batch window",
        "time_to_resolve_minutes": 10,
    },
    {
        "incident_id": "INC-2024-003",
        "alert_type": "high_cpu",
        "resource": "prod-server-02",
        "severity": "medium",
        "timestamp": "2025-01-10T03:45:00Z",
        "resolution": "false_positive",
        "root_cause": "Monitoring agent bug reporting inflated CPU values",
        "action_taken": "Updated monitoring agent to v3.2.1",
        "time_to_resolve_minutes": 30,
    },
    {
        "incident_id": "INC-2024-004",
        "alert_type": "high_memory",
        "resource": "prod-server-01",
        "severity": "critical",
        "timestamp": "2025-02-20T11:00:00Z",
        "resolution": "critical_confirmed",
        "root_cause": "OOM due to unbounded cache growth in order service",
        "action_taken": "Added cache eviction policy, increased memory limits",
        "time_to_resolve_minutes": 60,
    },
    {
        "incident_id": "INC-2024-005",
        "alert_type": "db_connection_pool_exhausted",
        "resource": "prod-db-primary",
        "severity": "critical",
        "timestamp": "2025-03-05T09:20:00Z",
        "resolution": "critical_confirmed",
        "root_cause": "Connection leak in payment service after v3.0 release",
        "action_taken": "Hotfixed connection cleanup, added connection pool monitoring",
        "time_to_resolve_minutes": 90,
    },
    {
        "incident_id": "INC-2024-006",
        "alert_type": "high_latency",
        "resource": "prod-server-01",
        "severity": "high",
        "timestamp": "2025-03-15T16:30:00Z",
        "resolution": "critical_confirmed",
        "root_cause": "Downstream service degradation cascading to frontend",
        "action_taken": "Enabled circuit breaker, increased timeout to 10s",
        "time_to_resolve_minutes": 35,
    },
    {
        "incident_id": "INC-2024-007",
        "alert_type": "disk_usage_high",
        "resource": "prod-server-01",
        "severity": "medium",
        "timestamp": "2025-03-20T22:00:00Z",
        "resolution": "false_positive",
        "root_cause": "Log rotation had not run; disk freed after cron triggered",
        "action_taken": "Verified cron job schedule, no action needed",
        "time_to_resolve_minutes": 5,
    },
    {
        "incident_id": "INC-2024-008",
        "alert_type": "pod_eviction",
        "resource": "prod-k8s-node-03",
        "severity": "high",
        "timestamp": "2025-04-01T06:00:00Z",
        "resolution": "critical_confirmed",
        "root_cause": "Node memory exhaustion due to resource limits misconfiguration",
        "action_taken": "Adjusted resource requests/limits, added node autoscaler",
        "time_to_resolve_minutes": 50,
    },
    {
        "incident_id": "INC-2024-009",
        "alert_type": "replication_lag",
        "resource": "prod-db-primary",
        "severity": "high",
        "timestamp": "2025-04-10T13:45:00Z",
        "resolution": "false_positive",
        "root_cause": "Large batch migration caused temporary lag, self-resolved",
        "action_taken": "No action needed; lag resolved within 5 minutes",
        "time_to_resolve_minutes": 5,
    },
    {
        "incident_id": "INC-2024-010",
        "alert_type": "high_error_rate",
        "resource": "prod-server-01",
        "severity": "critical",
        "timestamp": "2025-04-15T10:00:00Z",
        "resolution": "critical_confirmed",
        "root_cause": "Bad deployment v2.14.2 introduced breaking API change",
        "action_taken": "Rolled back to v2.14.1, fixed in v2.14.3",
        "time_to_resolve_minutes": 25,
    },
]


def lookup_historical_incidents(alert_type: str, resource: str = "") -> dict:
    """Searches the historical incident database for similar past incidents.

    Looks up past incidents matching the given alert type and optionally
    the specific resource. Returns matching incidents with their resolutions.

    Args:
        alert_type: The type of alert to search for (e.g., "high_cpu",
            "high_memory", "db_connection_pool_exhausted").
        resource: Optional resource name to narrow the search.
            If empty, returns all incidents matching the alert_type.

    Returns:
        A dictionary containing matching incidents and analysis summary.
    """
    # Find matching incidents
    matches = []
    for incident in _HISTORICAL_INCIDENTS:
        type_match = incident["alert_type"].lower() == alert_type.lower()
        resource_match = (
            not resource
            or incident["resource"].lower() == resource.lower()
        )
        if type_match and resource_match:
            matches.append(incident)

    # Also find incidents for the same resource (different alert types)
    resource_incidents = []
    if resource:
        for incident in _HISTORICAL_INCIDENTS:
            if (
                incident["resource"].lower() == resource.lower()
                and incident["alert_type"].lower() != alert_type.lower()
            ):
                resource_incidents.append(incident)

    # Analyze resolution patterns
    total_matches = len(matches)
    if total_matches > 0:
        critical_count = sum(
            1 for m in matches if m["resolution"] == "critical_confirmed"
        )
        false_positive_count = sum(
            1 for m in matches if m["resolution"] == "false_positive"
        )
        critical_rate = round(critical_count / total_matches * 100, 1)
        avg_resolve_time = round(
            sum(m["time_to_resolve_minutes"] for m in matches) / total_matches, 1
        )
    else:
        critical_count = 0
        false_positive_count = 0
        critical_rate = 0.0
        avg_resolve_time = 0.0

    return {
        "status": "success",
        "alert_type": alert_type,
        "resource_filter": resource or "all",
        "total_matches": total_matches,
        "matching_incidents": matches,
        "resource_other_incidents": resource_incidents,
        "analysis": {
            "critical_confirmed_count": critical_count,
            "false_positive_count": false_positive_count,
            "critical_rate_pct": critical_rate,
            "average_resolution_time_minutes": avg_resolve_time,
        },
        "summary": (
            f"Found {total_matches} historical incident(s) matching "
            f"alert_type='{alert_type}'"
            + (f" on resource='{resource}'" if resource else "")
            + f". Critical rate: {critical_rate}% "
            f"({critical_count} critical, {false_positive_count} false positive). "
            f"Average resolution time: {avg_resolve_time} minutes."
            + (
                f" Also found {len(resource_incidents)} other incident(s) "
                f"on this resource."
                if resource_incidents
                else ""
            )
        ),
    }
