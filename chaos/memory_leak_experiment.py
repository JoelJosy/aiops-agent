import time
import requests
from datetime import datetime, timezone
from experiment_utils import MEMORY_LEAK_URL
from incident_logger import log_incident

def run_memory_leak_experiment(duration_seconds: int, megabytes: int):
    """Trigger Memory Leak"""
    start_time, end_time = None, None
    try:
        print(f"\nAllocating simulated memory leak of {megabytes} MB...")
        requests.post(MEMORY_LEAK_URL, json={"megabytes": megabytes}).raise_for_status()

        start_time = datetime.now(timezone.utc)
        print(f"   Fault injected at: {start_time.strftime('%H:%M:%SZ')}")
        print(f"   Monitoring fault period for {duration_seconds} seconds...")
        time.sleep(duration_seconds)
    finally:
        # Keep in mind: Python may hold memory after deletion, 
        # but we call DELETE anyway to clear the internal Python array.
        print(f"\nHealing System (Resetting memory leak)...")
        requests.delete(MEMORY_LEAK_URL).raise_for_status()
        end_time = datetime.now(timezone.utc)
        print(f"   System healed at: {end_time.strftime('%H:%M:%SZ')}")

    log_incident("memory_leak", "aiops-app", start_time, end_time, {"allocated_mb": megabytes})