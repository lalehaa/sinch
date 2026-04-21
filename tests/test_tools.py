"""Unit tests for Incident Manager tools."""

import json
import pytest

from incident_manager.tools.alert_analyzer import analyze_alert
from incident_manager.tools.log_querier import query_logs
from incident_manager.tools.incident_lookup import lookup_historical_incidents
from incident_manager.tools.pattern_matcher import check_pattern


# ============================================================
# Tests for analyze_alert
# ============================================================

class TestAnalyzeAlert:
    """Tests for the alert analyzer tool."""

    def test_parse_critical_alert(self):
        """Critical high-CPU alert should yield high risk level."""
        alert = json.dumps({
            "alert_id": "test-001",
            "alert_type": "high_cpu",
            "resource": "prod-server-01",
            "severity": "critical",
            "metric_name": "cpu_utilization",
            "metric_value": 98.5,
            "threshold": 80.0,
            "description": "CPU utilization exceeded threshold",
        })
        result = analyze_alert(alert)

        assert result["status"] == "success"
        assert result["alert_id"] == "test-001"
        assert result["alert_type"] == "high_cpu"
        assert result["severity"] == "critical"
        assert result["severity_score"] == 4
        assert result["initial_risk_level"] == "high"
        assert result["threshold_breach_percentage"] > 0

    def test_parse_low_severity_alert(self):
        """Low severity alert with minor breach should yield low risk level."""
        alert = json.dumps({
            "alert_id": "test-002",
            "alert_type": "disk_usage",
            "resource": "prod-server-02",
            "severity": "low",
            "metric_name": "disk_usage_pct",
            "metric_value": 72,
            "threshold": 70,
        })
        result = analyze_alert(alert)

        assert result["status"] == "success"
        assert result["severity_score"] == 1
        assert result["initial_risk_level"] == "low"

    def test_parse_invalid_json(self):
        """Invalid JSON should return error status."""
        result = analyze_alert("not valid json {{{")

        assert result["status"] == "error"
        assert "Failed to parse" in result["message"]

    def test_parse_missing_fields(self):
        """Missing fields should use defaults gracefully."""
        result = analyze_alert(json.dumps({"alert_type": "unknown_alert"}))

        assert result["status"] == "success"
        assert result["alert_id"] == "unknown"
        assert result["resource"] == "unknown"

    def test_parse_dict_input(self):
        """Should accept dict input directly (not just JSON strings)."""
        result = analyze_alert({
            "alert_id": "dict-001",
            "alert_type": "test",
            "resource": "test-resource",
            "severity": "medium",
        })

        assert result["status"] == "success"
        assert result["alert_id"] == "dict-001"


# ============================================================
# Tests for query_logs
# ============================================================

class TestQueryLogs:
    """Tests for the log querier tool."""

    def test_query_known_resource(self):
        """Querying a known resource should return mock log entries."""
        result = query_logs("prod-server-01", time_window_minutes=30)

        assert result["status"] == "success"
        assert result["resource"] == "prod-server-01"
        assert result["total_entries"] > 0
        assert result["error_count"] > 0
        assert result["has_errors"] is True

    def test_query_healthy_resource(self):
        """Querying a healthy resource should return clean logs."""
        result = query_logs("prod-server-02", time_window_minutes=30)

        assert result["status"] == "success"
        assert result["error_count"] == 0
        assert result["has_errors"] is False
        assert result["error_pattern"] == "none"

    def test_query_unknown_resource(self):
        """Unknown resource should return default (healthy) logs."""
        result = query_logs("unknown-resource", time_window_minutes=30)

        assert result["status"] == "success"
        assert result["total_entries"] > 0
        assert result["error_count"] == 0

    def test_narrow_time_window(self):
        """Narrow time window should filter old entries."""
        result_narrow = query_logs("prod-server-01", time_window_minutes=5)
        result_wide = query_logs("prod-server-01", time_window_minutes=60)

        assert result_narrow["total_entries"] <= result_wide["total_entries"]

    def test_log_entries_have_required_fields(self):
        """Each log entry should have timestamp, severity, resource, message."""
        result = query_logs("prod-server-01")

        for entry in result["log_entries"]:
            assert "timestamp" in entry
            assert "severity" in entry
            assert "resource" in entry
            assert "message" in entry


# ============================================================
# Tests for lookup_historical_incidents
# ============================================================

class TestLookupHistoricalIncidents:
    """Tests for the incident lookup tool."""

    def test_lookup_by_alert_type(self):
        """Looking up a known alert type should return matches."""
        result = lookup_historical_incidents("high_cpu")

        assert result["status"] == "success"
        assert result["total_matches"] > 0
        assert len(result["matching_incidents"]) > 0

    def test_lookup_by_type_and_resource(self):
        """Filtering by resource should narrow results."""
        result_all = lookup_historical_incidents("high_cpu")
        result_filtered = lookup_historical_incidents("high_cpu", "prod-server-01")

        assert result_filtered["total_matches"] <= result_all["total_matches"]
        # All matches should be for the filtered resource
        for inc in result_filtered["matching_incidents"]:
            assert inc["resource"] == "prod-server-01"

    def test_lookup_unknown_alert_type(self):
        """Unknown alert type should return zero matches."""
        result = lookup_historical_incidents("totally_new_alert_type")

        assert result["status"] == "success"
        assert result["total_matches"] == 0
        assert len(result["matching_incidents"]) == 0

    def test_analysis_stats(self):
        """Analysis should include critical rate and resolution stats."""
        result = lookup_historical_incidents("high_cpu", "prod-server-01")

        analysis = result["analysis"]
        assert "critical_confirmed_count" in analysis
        assert "false_positive_count" in analysis
        assert "critical_rate_pct" in analysis
        assert "average_resolution_time_minutes" in analysis

    def test_resource_other_incidents(self):
        """Should return other incident types for the same resource."""
        result = lookup_historical_incidents("high_cpu", "prod-server-01")

        # prod-server-01 has other types of incidents too
        assert len(result["resource_other_incidents"]) > 0


# ============================================================
# Tests for check_pattern
# ============================================================

class TestCheckPattern:
    """Tests for the pattern matcher tool."""

    def test_critical_pattern(self):
        """Alert with strong critical signals should get high confidence."""
        alert_data = json.dumps({
            "alert_type": "high_cpu",
            "severity": "critical",
            "initial_risk_level": "high",
            "has_errors": True,
            "error_pattern": "error_spike",
            "threshold_breach_percentage": 60,
        })
        historical_data = json.dumps({
            "total_matches": 3,
            "analysis": {
                "critical_rate_pct": 80,
                "false_positive_count": 0,
                "critical_confirmed_count": 3,
            },
            "matching_incidents": [
                {"incident_id": "INC-001"},
                {"incident_id": "INC-002"},
                {"incident_id": "INC-003"},
            ],
        })

        result = check_pattern(alert_data, historical_data)

        assert result["status"] == "success"
        assert result["pattern_found"] is True
        assert result["confidence_score"] >= 0.7
        assert result["recommendation"] == "critical"

    def test_false_positive_pattern(self):
        """Alert matching false-positive history should get low confidence."""
        alert_data = json.dumps({
            "alert_type": "disk_usage",
            "severity": "low",
            "initial_risk_level": "low",
            "has_errors": False,
            "error_pattern": "none",
            "threshold_breach_percentage": 3,
        })
        historical_data = json.dumps({
            "total_matches": 4,
            "analysis": {
                "critical_rate_pct": 10,
                "false_positive_count": 3,
                "critical_confirmed_count": 0,
            },
            "matching_incidents": [{"incident_id": "INC-007"}],
        })

        result = check_pattern(alert_data, historical_data)

        assert result["status"] == "success"
        assert result["confidence_score"] <= 0.3
        assert result["recommendation"] == "false_positive"

    def test_novel_alert_needs_investigation(self):
        """Novel alert with no history should need investigation."""
        alert_data = json.dumps({
            "alert_type": "new_type",
            "severity": "medium",
            "initial_risk_level": "medium",
            "has_errors": False,
            "error_pattern": "none",
            "threshold_breach_percentage": 10,
        })
        historical_data = json.dumps({
            "total_matches": 0,
            "analysis": {
                "critical_rate_pct": 0,
                "false_positive_count": 0,
                "critical_confirmed_count": 0,
            },
            "matching_incidents": [],
        })

        result = check_pattern(alert_data, historical_data)

        assert result["status"] == "success"
        assert result["pattern_found"] is False
        assert result["recommendation"] == "needs_investigation"

    def test_invalid_json_returns_error(self):
        """Invalid JSON input should return error."""
        result = check_pattern("bad json {{{", "also bad {{{")

        assert result["status"] == "error"

    def test_confidence_bounded(self):
        """Confidence score should always be between 0 and 1."""
        # Extreme critical signals
        alert_data = json.dumps({
            "severity": "critical",
            "has_errors": True,
            "error_pattern": "critical_errors_present",
            "threshold_breach_percentage": 200,
        })
        historical_data = json.dumps({
            "total_matches": 10,
            "analysis": {"critical_rate_pct": 100},
            "matching_incidents": [{"incident_id": f"INC-{i}"} for i in range(10)],
        })

        result = check_pattern(alert_data, historical_data)

        assert 0.0 <= result["confidence_score"] <= 1.0
