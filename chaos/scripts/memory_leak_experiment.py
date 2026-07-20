import time
import requests
from datetime import datetime, timezone
from chaos.scripts.experiment_utils import MEMORY_LEAK_URL
from chaos.incident_logger import log_incident
from service.logger import logger

def run_memory_leak_experiment(duration_seconds: int, megabytes: int, steps: int = 5):
    """Trigger a stepped, continuous Memory Leak"""
    start_time, end_time = None, None
    mb_per_step = megabytes // steps
    time_per_step = duration_seconds / steps

    try:
        print(f"\nStarting stepped memory leak: total {megabytes} MB across {steps} steps...")
        start_time = datetime.now(timezone.utc)
        print(f"   Fault started at: {start_time.strftime('%H:%M:%SZ')}")

        for step in range(steps):
            print(f"   [Step {step+1}/{steps}] Injecting additional {mb_per_step} MB...")
            requests.post(MEMORY_LEAK_URL, json={"megabytes": mb_per_step}).raise_for_status()
            
            # Wait out the slice for this step
            time.sleep(time_per_step)

    finally:
        print(f"\n   Healing System (Resetting memory leak)...")
        requests.delete(MEMORY_LEAK_URL).raise_for_status()
        end_time = datetime.now(timezone.utc)
        print(f"   System healed at: {end_time.strftime('%H:%M:%SZ')}")

    log_incident("memory_leak", "aiops-app", start_time, end_time, {"allocated_mb": megabytes})