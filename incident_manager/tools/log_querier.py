"""Log Querier Tool — Queries Cloud Logging for related log entries.

V1 uses mock data simulating Cloud Logging responses.
For production, replace with google-cloud-logging client.
"""

import random
from datetime import datetime, timedelta


# --- Mock Log Database ---
# Simulates log entries that would come from Cloud Logging

_MOCK_LOG_ENTRIES = {
    "prod-server-01": [
        {"severity": "ERROR", "message": "Connection pool exhausted. Active connections: 500/500", "offset_min": -2},
        {"severity": "ERROR", "message": "Request timeout after 30000ms on /api/v2/orders", "offset_min": -3},
        {"severity": "WARNING", "message": "CPU usage exceeded 90% for 5 minutes", "offset_min": -5},
        {"severity": "ERROR", "message": "OOM killer invoked, process nginx (pid 4521) killed", "offset_min": -7},
        {"severity": "INFO", "message": "Health check passed on /healthz", "offset_min": -10},
        {"severity": "WARNING", "message": "Disk usage at 85% on /var/log", "offset_min": -15},
        {"severity": "INFO", "message": "Deployment completed: v2.14.3 → v2.14.4", "offset_min": -60},
    ],
    "prod-server-02": [
        {"severity": "INFO", "message": "Health check passed on /healthz", "offset_min": -1},
        {"severity": "INFO", "message": "Request latency p99: 120ms", "offset_min": -5},
        {"severity": "DEBUG", "message": "Cache hit ratio: 94.2%", "offset_min": -10},
    ],
    "prod-db-primary": [
        {"severity": "ERROR", "message": "Replication lag exceeded 10s on replica prod-db-replica-02", "offset_min": -1},
        {"severity": "WARNING", "message": "Slow query detected: SELECT * FROM orders WHERE... (took 12.4s)", "offset_min": -3},
        {"severity": "ERROR", "message": "Max connections reached: 300/300", "offset_min": -5},
        {"severity": "WARNING", "message": "InnoDB buffer pool usage at 92%", "offset_min": -8},
        {"severity": "INFO", "message": "Automated backup completed successfully", "offset_min": -120},
    ],
    "prod-k8s-node-03": [
        {"severity": "WARNING", "message": "Pod evicted due to memory pressure: api-gateway-7f8b9c", "offset_min": -2},
        {"severity": "ERROR", "message": "Node memory pressure: available 256Mi of 16Gi", "offset_min": -3},
        {"severity": "WARNING", "message": "kubelet: PLEG is not healthy", "offset_min": -5},
        {"severity": "INFO", "message": "Node condition MemoryPressure changed to True", "offset_min": -6},
    ],
}

# Default logs for unknown resources
_DEFAULT_LOGS = [
    {"severity": "INFO", "message": "Health check passed", "offset_min": -1},
    {"severity": "INFO", "message": "Service running normally", "offset_min": -5},
    {"severity": "DEBUG", "message": "Metrics collection completed", "offset_min": -10},
]


def query_logs(resource_name: str, time_window_minutes: int = 30) -> dict:
    """Queries recent log entries for a specific resource.

    Fetches log entries from Cloud Logging (or mock data in V1) for the
    specified resource within the given time window.

    Args:
        resource_name: The name of the resource to query logs for
            (e.g., "prod-server-01", "prod-db-primary").
        time_window_minutes: How many minutes of recent logs to retrieve.
            Defaults to 30 minutes.

    Returns:
        A dictionary containing the log entries and a summary analysis.
    """
    now = datetime.utcnow()
    raw_entries = _MOCK_LOG_ENTRIES.get(resource_name, _DEFAULT_LOGS)

    # Filter entries within the time window
    entries = []
    for entry in raw_entries:
        if abs(entry["offset_min"]) <= time_window_minutes:
            entry_time = now + timedelta(minutes=entry["offset_min"])
            entries.append({
                "timestamp": entry_time.isoformat() + "Z",
                "severity": entry["severity"],
                "resource": resource_name,
                "message": entry["message"],
            })

    # Compute summary stats
    error_count = sum(1 for e in entries if e["severity"] == "ERROR")
    warning_count = sum(1 for e in entries if e["severity"] == "WARNING")
    critical_count = sum(1 for e in entries if e["severity"] == "CRITICAL")

    has_errors = error_count > 0 or critical_count > 0
    error_pattern = "none"
    if critical_count > 0:
        error_pattern = "critical_errors_present"
    elif error_count >= 3:
        error_pattern = "error_spike"
    elif error_count > 0:
        error_pattern = "some_errors"

    return {
        "status": "success",
        "resource": resource_name,
        "time_window_minutes": time_window_minutes,
        "total_entries": len(entries),
        "error_count": error_count,
        "warning_count": warning_count,
        "critical_count": critical_count,
        "has_errors": has_errors,
        "error_pattern": error_pattern,
        "log_entries": entries,
        "summary": (
            f"Found {len(entries)} log entries for '{resource_name}' "
            f"in the last {time_window_minutes} minutes. "
            f"Errors: {error_count}, Warnings: {warning_count}, "
            f"Critical: {critical_count}. "
            f"Error pattern: {error_pattern}."
        ),
    }
