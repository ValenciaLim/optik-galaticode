import requests
import json
import time
import random

# --- Configuration ---
# This must match the agent ID used in the onboarding curl command
AGENT_ID = "demo-agent"
TELEMETRY_ENDPOINT = "http://localhost:8080/api/telemetry"
POST_INTERVAL_SECONDS = 3

def generate_telemetry_payload():
    """Creates a randomized telemetry payload."""
    return {
        "score": round(random.uniform(0.1, 0.99), 2),
        "latency_ms": random.randint(50, 500),
        "error_count": random.choice([0, 0, 0, 0, 1, 2]), # Skew towards zero errors
        "prompt_tokens": random.randint(100, 1000),
        "completion_tokens": random.randint(50, 500),
    }

def post_telemetry():
    """Constructs and posts the telemetry data to the endpoint."""
    payload = {
        "agent_id": AGENT_ID,
        "payload": generate_telemetry_payload()
    }

    try:
        response = requests.post(TELEMETRY_ENDPOINT, json=payload, timeout=5)
        
        if response.status_code == 200:
            print(f"Successfully sent telemetry for {AGENT_ID}: {payload['payload']}")
        else:
            print(f"Error sending telemetry: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Failed to connect to the telemetry endpoint: {e}")

if __name__ == "__main__":
    print(f"--- Telemetry Demo Client Started for Agent: {AGENT_ID} ---")
    print(f"Posting data to {TELEMETRY_ENDPOINT} every {POST_INTERVAL_SECONDS} seconds.")
    print("Press Ctrl+C to stop.")
    
    while True:
        post_telemetry()
        time.sleep(POST_INTERVAL_SECONDS) 