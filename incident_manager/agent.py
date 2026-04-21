"""Incident Manager AI Assistant — ADK Agent Definition."""

from google.adk.agents.llm_agent import Agent

from .prompts import INCIDENT_MANAGER_INSTRUCTION, INCIDENT_MANAGER_DESCRIPTION
from .tools import (
    analyze_alert,
    query_logs,
    lookup_historical_incidents,
    check_pattern,
)

root_agent = Agent(
    model="gemini-2.0-flash",
    name="incident_manager",
    description=INCIDENT_MANAGER_DESCRIPTION,
    instruction=INCIDENT_MANAGER_INSTRUCTION,
    tools=[
        analyze_alert,
        query_logs,
        lookup_historical_incidents,
        check_pattern,
    ],
)
