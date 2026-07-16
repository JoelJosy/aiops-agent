import subprocess
import time
from datetime import datetime, timezone

from incident_logger import log_incident

from scripts.experiment_utils import poll_health


def run_outage_experiment(duration_seconds: int, target: str):
    """Executes a real app container outage via Docker Compose."""
    start_time = None
    end_time = None

    try:
        print(f"\nStopping {target} container...")
        subprocess.run(["docker", "compose", "stop", "aiops-app"], check=True)

        start_time = datetime.now(timezone.utc)
        print(f"   Outage started at: {start_time.strftime('%H:%M:%SZ')}")
        print(f"   Monitoring outage period for {duration_seconds} seconds...")
        time.sleep(duration_seconds)

    finally:
        # Guaranteed to run in finally block so your stack isn't left broken!
        print(f"\nRestarting {target} container...")
        subprocess.run(["docker", "compose", "start", "aiops-app"], check=True)

        # Wait for the python app inside the container to actually respond to HTTP traffic
        poll_health()

        end_time = datetime.now(timezone.utc)
        print(f"   Outage recovery complete at: {end_time.strftime('%H:%M:%SZ')}")

    log_incident(
        fault_type="app_outage",
        target="aiops-app",
        start=start_time,
        end=end_time,
        params={},
    )