import requests
import time
from datetime import datetime, timezone

from chaos.incident_logger import log_incident
from service.logger import logger
from chaos.scripts.experiment_utils import CPU_BURN_URL

def run_cpu_spike_experiment(duration_seconds: int, workers: int):
    """Trigger CPU Spike"""
    start_time, end_time = None, None
    try:
        print(f"\nLaunching CPU Burner with {workers} threads...")
        requests.post(CPU_BURN_URL, json={"workers": workers}).raise_for_status()
        start_time = datetime.now(timezone.utc)
        print(f"   Fault injected at: {start_time.strftime('%H:%M:%SZ')}")
        print(f"   Monitoring fault period for {duration_seconds} seconds...")
        time.sleep(duration_seconds)
    finally:
        print(f"\nHealing System (Resetting CPU spike)...")
        requests.delete(CPU_BURN_URL).raise_for_status()
        end_time = datetime.now(timezone.utc)
        print(f"   System healed at: {end_time.strftime('%H:%M:%SZ')}")

    log_incident("cpu_spike", "aiops-app", start_time, end_time, {"workers": workers})