import base64
import json
import os
import requests
import functions_framework
from google.cloud import pubsub_v1

# URLs and Configuration set via Environment Variables
AGENT_URL = os.environ.get("AGENT_URL")
PROJECT_ID = os.environ.get("PROJECT_ID", "agent-project-459312")
RESULTS_TOPIC = os.environ.get("RESULTS_TOPIC", "analysis-results-topic")

# Initialize the Pub/Sub publisher client (it's best to do this globally for performance)
publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(PROJECT_ID, RESULTS_TOPIC)

# Triggered from a message on a Cloud Pub/Sub topic.
@functions_framework.cloud_event
def handle_alert(cloud_event):
    """Pub/Sub Cloud Function that forwards alerts to the Incident Manager Agent, then publishes the result."""
    
    # 1. Parse the incoming Pub/Sub message
    print(f"Received CloudEvent: {cloud_event.data}")
    try:
        # Pub/Sub messages are base64 encoded
        pubsub_message = base64.b64decode(cloud_event.data["message"]["data"]).decode('utf-8')
        request_json = json.loads(pubsub_message)
    except Exception as e:
        print(f"Error parsing Pub/Sub message: {e}")
        # Default payload if parsing fails
        request_json = {
            "alert_id": "cf-pubsub-test-001",
            "alert_type": "high_cpu",
            "resource": "prod-server-01",
            "severity": "critical",
            "metric_name": "cpu_usage",
            "metric_value": 98,
            "threshold": 80
        }

    if not AGENT_URL:
        print("Error: AGENT_URL environment variable is missing")
        return

    # 2. Build the endpoint URL for your deployed agent
    target_endpoint = f"{AGENT_URL.rstrip('/')}/analyze"

    try:
        # 3. Call the Cloud Run agent, passing the alert data as JSON
        # LLM tools take a few seconds to run, so set a longer timeout (e.g., 60s)
        response = requests.post(target_endpoint, json=request_json, timeout=60)
        response.raise_for_status()
        
        # 4. Get the Agent's analysis verdict
        verdict = response.json()
        print(f"Agent Verdict received, publishing to {RESULTS_TOPIC}...")
        
        # 5. Publish the verdict to the downstream Pub/Sub topic
        # Ensure the payload is serialized to a JSON string and encoded to bytes
        message_bytes = json.dumps(verdict).encode("utf-8")
        
        future = publisher.publish(topic_path, data=message_bytes)
        message_id = future.result() # This blocks until the publish is confirmed
        print(f"Published verdict with Message ID: {message_id}")

    except Exception as e:
        print(f"Failed to call agent or publish result: {str(e)}")

