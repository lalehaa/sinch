FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Cloud Run injects the PORT environment variable
ENV PORT=8080
EXPOSE 8080

# Run the FastAPI server — use shell form so $PORT is resolved at runtime
CMD uvicorn server.main:app --host 0.0.0.0 --port $PORT
