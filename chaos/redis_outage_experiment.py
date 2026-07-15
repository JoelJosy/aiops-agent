import subprocess
import time
from datetime import datetime, timezone

from incident_logger import log_incident

from experiment_utils import poll_redis


def run_redis_outage_experiment(duration_seconds: int):
    """Executes a physical Redis container outage via Docker Compose."""
    start_time = None
    end_time = None
    try:
        print(f"\nStopping redis container...")
        subprocess.run(["docker", "compose", "stop", "redis"], check=True)
        start_time = datetime.now(timezone.utc)
        print(f"   Redis outage started at: {start_time.strftime('%H:%M:%SZ')}")
        print(f"   Monitoring outage period for {duration_seconds} seconds...")
        time.sleep(duration_seconds)
    finally:
        # try/finally guarantees Redis will be restarted even if the test run crashes
        print(f"\nRestarting redis container...")
        subprocess.run(["docker", "compose", "start", "redis"], check=True)

        # Wait for the Redis container to actually respond to commands
        poll_redis()

        end_time = datetime.now(timezone.utc)
        print(f"   Redis recovery complete at: {end_time.strftime('%H:%M:%SZ')}")

    log_incident(
        fault_type="redis_outage",
        target="redis",
        start=start_time,
        end=end_time,
        params={},
    )