import time
from datetime import datetime, timezone

import requests

from incident_logger import log_incident

from scripts.experiment_utils import CHAOS_URL


def run_latency_experiment(duration_seconds: int, delay_ms: int):
    """Executes a simulated Redis latency injection."""
    start_time = None
    end_time = None

    try:
        print(f"\nInjecting Redis Latency...")
        print(f"   POST {CHAOS_URL} with delay_ms={delay_ms}")
        response = requests.post(CHAOS_URL, json={"delay_ms": delay_ms})
        response.raise_for_status()

        start_time = datetime.now(timezone.utc)
        print(f"Fault injected at: {start_time.strftime('%H:%M:%SZ')}")
        print(f"Monitoring fault period for {duration_seconds} seconds...")
        time.sleep(duration_seconds)

    finally:
        print(f"\nHealing System (Resetting delay to 0)...")
        response = requests.delete(CHAOS_URL)
        response.raise_for_status()
        end_time = datetime.now(timezone.utc)
        print(f"System healed at: {end_time.strftime('%H:%M:%SZ')}")

    log_incident(
        fault_type="redis_latency",
        target="aiops-app",
        start=start_time,
        end=end_time,
        params={"delay_ms": delay_ms},
    )