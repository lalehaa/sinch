"""FastAPI server — bridges Pub/Sub (via Eventarc) to the ADK agent.

This server receives CloudEvent HTTP POST requests from Eventarc when
a message is published to the alerts Pub/Sub topic. It decodes the
message and sends it to the ADK agent for analysis.

It also exposes a /analyze endpoint for direct HTTP testing.
"""

import base64
import json
import logging
import os
import uuid

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from incident_manager.agent import root_agent

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Incident Manager AI Assistant",
    description=(
        "ADK-powered agent that analyzes alerts and determines if they are "
        "critical incidents or false positives."
    ),
    version="1.0.0",
)

# Initialize ADK session service and runner
session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name="incident_manager",
    session_service=session_service,
)


async def _run_agent(alert_data: dict) -> dict:
    """Run the ADK agent with the given alert data.

    Args:
        alert_data: Dictionary containing alert information.

    Returns:
        Dictionary with the agent's analysis verdict.
    """
    # Create a unique session for each alert
    user_id = "alert-system"
    session_id = f"alert-{uuid.uuid4().hex[:12]}"

    session = session_service.create_session(
        app_name="incident_manager",
        user_id=user_id,
        session_id=session_id,
    )

    # Format alert as a message to the agent
    alert_json = json.dumps(alert_data, indent=2)
    prompt = (
        f"Analyze the following alert and determine if it is critical "
        f"or a false positive:\n\n```json\n{alert_json}\n```"
    )

    # Create the user message
    user_message = types.Content(
        role="user",
        parts=[types.Part(text=prompt)],
    )

    # Run the agent and collect response
    agent_response_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=user_message,
    ):
        if event.is_final_response():
            for part in event.content.parts:
                if part.text:
                    agent_response_text += part.text

    return {
        "alert_id": alert_data.get("alert_id", "unknown"),
        "session_id": session_id,
        "agent_response": agent_response_text,
    }


@app.post("/")
async def handle_pubsub_event(request: Request):
    """Receives CloudEvent from Eventarc (Pub/Sub trigger).

    Eventarc delivers Pub/Sub messages as CloudEvent HTTP POST requests.
    The message data is base64-encoded in the request body.
    """
    try:
        envelope = await request.json()
        logger.info(f"Received CloudEvent: {json.dumps(envelope)[:200]}...")

        # Extract the Pub/Sub message from the CloudEvent envelope
        message = envelope.get("message", {})
        if not message:
            # Try alternative CloudEvent format
            message = envelope

        # Decode base64 data
        data_b64 = message.get("data", "")
        if data_b64:
            decoded = base64.b64decode(data_b64).decode("utf-8")
            alert_data = json.loads(decoded)
        else:
            # If no base64 envelope, try to use the body directly
            alert_data = envelope

        logger.info(f"Processing alert: {alert_data.get('alert_id', 'unknown')}")

        # Run the agent
        result = await _run_agent(alert_data)

        logger.info(
            f"Agent verdict for alert {result['alert_id']}: "
            f"{result['agent_response'][:200]}..."
        )

        return JSONResponse(content=result, status_code=200)

    except Exception as e:
        logger.error(f"Error processing event: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze")
async def analyze_alert_direct(request: Request):
    """Direct HTTP endpoint for testing — bypasses Pub/Sub.

    Send a raw alert JSON payload directly to the agent.

    Example:
        curl -X POST http://localhost:8080/analyze \\
            -H "Content-Type: application/json" \\
            -d '{"alert_id": "test-001", "alert_type": "high_cpu", ...}'
    """
    try:
        alert_data = await request.json()
        logger.info(
            f"Direct analysis request for alert: "
            f"{alert_data.get('alert_id', 'unknown')}"
        )

        result = await _run_agent(alert_data)
        return JSONResponse(content=result, status_code=200)

    except Exception as e:
        logger.error(f"Error in direct analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """Health check endpoint for Cloud Run."""
    return {"status": "healthy", "agent": "incident_manager", "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
