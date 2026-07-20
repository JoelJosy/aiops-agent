import requests
import time
from datetime import datetime, timezone

from chaos.incident_logger import log_incident
from service.logger import logger
from scripts.experiment_utils import DOWNSTREAM_FAILURE_URL


def run_downstream_failure_experiment(duration_seconds: int, failure_rate: float):
    """ Simulate downstream service failure"""
    start_time, end_time = None, None
    try:
        print(f"\nInjecting Downstream Failures...")
        requests.post(DOWNSTREAM_FAILURE_URL, json={"failure_rate": failure_rate}).raise_for_status()
        start_time = datetime.now(timezone.utc)
        print(f"   Fault injected at: {start_time.strftime('%H:%M:%SZ')}")
        print(f"   Monitoring fault period for {duration_seconds} seconds...")
        time.sleep(duration_seconds)
    finally:
        print(f"\nHealing System (Resetting downstream delay to 0)...")
        requests.delete(DOWNSTREAM_FAILURE_URL).raise_for_status()
        end_time = datetime.now(timezone.utc)
        print(f"   System healed at: {end_time.strftime('%H:%M:%SZ')}")

    log_incident("downstream_failure", "aiops-app", start_time, end_time, {"dependency": "catalog-service", "failure_rate": failure_rate})