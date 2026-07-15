import requests
import time
from datetime import datetime, timezone

from incident_logger import log_incident
from experiment_utils import CPU_BURN_URL

def run_cpu_spike_experiment(duration_seconds: int, workers: int):
    """Trigger CPU Spike"""
    start_time, end_time = None, None
    try:
        print(f"\nLaunching CPU Burner with {workers} threads...")
        requests.post(CPU_BURN_URL, json={"workers": workers}).raise_for_status()
        start_time = datetime.now(timezone.utc)
        time.sleep(duration_seconds)
    finally:
        requests.delete(CPU_BURN_URL).raise_for_status()
        end_time = datetime.now(timezone.utc)

    log_incident("cpu_spike", "aiops-app", start_time, end_time, {"workers": workers})