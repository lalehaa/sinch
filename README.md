# Incident Manager AI Assistant

An ADK (Agent Development Kit) agent that analyzes incoming alerts, cross-references them with logs, historical incidents, and past actions, then determines if an alert is **critical** or a **false positive**.

## Architecture

```
Alert Source → Pub/Sub → Eventarc → Cloud Run (ADK Agent + FastAPI) → Verdict
```

## Project Structure

```
sinch/
├── incident_manager/           # ADK agent package
│   ├── __init__.py             # Exports root_agent
│   ├── agent.py                # Agent definition
│   ├── prompts.py              # System instruction prompt
│   ├── schemas.py              # Data models
│   └── tools/                  # Agent tools
│       ├── alert_analyzer.py   # Parse and classify alerts
│       ├── log_querier.py      # Query Cloud Logging (mock)
│       ├── incident_lookup.py  # Historical incidents (mock)
│       └── pattern_matcher.py  # Pattern matching logic
├── server/
│   └── main.py                 # FastAPI server
├── tests/                      # Unit tests
├── .env                        # Configuration
├── requirements.txt            # Dependencies
└── Dockerfile                  # Cloud Run deployment
```

## Setup

### 1. Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

Edit `.env` with your credentials:

```bash
# Option A: Google AI Studio (simplest for local dev)
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your-api-key-here

# Option B: Vertex AI (recommended for production)
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

### 3. Run Locally

**Option A: ADK Web UI** (interactive chat interface)
```bash
adk web
```
Open http://localhost:8000 and select `incident_manager`.

**Option B: FastAPI Server** (API endpoint)
```bash
uvicorn server.main:app --reload --port 8080
```

### 4. Test with curl

```bash
curl -X POST http://localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "alert_id": "test-001",
    "alert_type": "high_cpu",
    "resource": "prod-server-01",
    "severity": "critical",
    "metric_name": "cpu_utilization",
    "metric_value": 98.5,
    "threshold": 80.0,
    "description": "CPU utilization exceeded threshold"
  }'
```

## Deploy to Cloud Run

### 1. Deploy the Service

```bash
adk deploy cloud_run \
  --project=YOUR_PROJECT \
  --region=us-central1
```

Or manually:

```bash
gcloud run deploy incident-manager \
  --source=. \
  --region=us-central1 \
  --allow-unauthenticated=false
```

### 2. Create Pub/Sub Topic

```bash
gcloud pubsub topics create alerts-topic
```

### 3. Create Eventarc Trigger

```bash
gcloud eventarc triggers create incident-alert-trigger \
  --location=us-central1 \
  --destination-run-service=incident-manager \
  --destination-run-region=us-central1 \
  --event-filters="type=google.cloud.pubsub.topic.v1.messagePublished" \
  --transport-topic=alerts-topic \
  --service-account=YOUR_SA@YOUR_PROJECT.iam.gserviceaccount.com
```

### 4. Test End-to-End

```bash
gcloud pubsub topics publish alerts-topic \
  --message='{"alert_id":"test-e2e","alert_type":"high_cpu","resource":"prod-server-01","severity":"critical","metric_value":98.5,"threshold":80}'
```

## Running Tests

```bash
pytest tests/ -v
```

## Agent Tools

| Tool | Purpose |
|------|---------|
| `analyze_alert` | Parses raw alert JSON, extracts key fields, computes initial risk level |
| `query_logs` | Fetches recent log entries for the affected resource |
| `lookup_historical_incidents` | Searches past incidents for similar alerts |
| `check_pattern` | Compares current alert against historical patterns, returns confidence score |
