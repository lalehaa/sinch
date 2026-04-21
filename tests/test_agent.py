"""Tests for the Incident Manager agent definition."""

import pytest

from incident_manager.agent import root_agent
from incident_manager.prompts import INCIDENT_MANAGER_INSTRUCTION


class TestAgentDefinition:
    """Tests for the agent configuration."""

    def test_agent_exists(self):
        """Agent should be properly instantiated."""
        assert root_agent is not None

    def test_agent_name(self):
        """Agent should have the expected name."""
        assert root_agent.name == "incident_manager"

    def test_agent_has_model(self):
        """Agent should have a model configured."""
        assert root_agent.model is not None

    def test_agent_has_tools(self):
        """Agent should have 4 tools configured."""
        assert len(root_agent.tools) == 4

    def test_agent_has_instruction(self):
        """Agent should have a non-empty system instruction."""
        assert root_agent.instruction is not None
        assert len(root_agent.instruction) > 100

    def test_instruction_contains_key_sections(self):
        """Instruction should cover the analysis workflow."""
        instruction = INCIDENT_MANAGER_INSTRUCTION
        assert "analyze_alert" in instruction
        assert "query_logs" in instruction
        assert "lookup_historical_incidents" in instruction
        assert "check_pattern" in instruction
        assert "CRITICAL" in instruction
        assert "FALSE POSITIVE" in instruction
        assert "NEEDS INVESTIGATION" in instruction
