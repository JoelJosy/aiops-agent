import argparse
import time
from datetime import datetime, timezone
import requests
from incident_logger import log_incident

# Configuration
APP_URL = "http://localhost:8000"
CHAOS_URL = f"{APP_URL}/chaos/redis-delay"


def run_experiment(baseline_seconds: int, duration_seconds: int, delay_ms: int):
    print(f"Starting Chaos Experiment Runner")
    print(f"=========================================")
    print(f"Phase 1: Baseline Period ({baseline_seconds} seconds)")
    print(f"   Waiting for system to gather normal metric traffic...")
    
    # Wait out the baseline
    time.sleep(baseline_seconds)
    
    # Track the exact bounds of our fault window
    start_time = None
    end_time = None

    try:
        # Phase 2: Inject the Fault
        print(f"\nPhase 2: Injecting Fault...")
        print(f"   POST {CHAOS_URL} with delay_ms={delay_ms}")
        
        response = requests.post(CHAOS_URL, json={"delay_ms": delay_ms})
        response.raise_for_status()
        
        # Capture the true UTC start time of the failure window
        start_time = datetime.now(timezone.utc)
        print(f"    Fault injected successfully at: {start_time.strftime('%H:%M:%SZ')}")
        print(f"    Monitoring fault period for {duration_seconds} seconds...")
        
        # Wait out the injection duration
        time.sleep(duration_seconds)

    except Exception as e:
        print(f"   Error occurred during fault injection: {e}")
        
    finally:
        # Phase 3: Heal the System
        print(f"\nPhase 3: Healing System (Resetting delay to 0)...")
        try:
            response = requests.delete(CHAOS_URL)
            response.raise_for_status()
            
            # Capture the true UTC end time of the failure window
            end_time = datetime.now(timezone.utc)
            print(f"   System healed successfully at: {end_time.strftime('%H:%M:%SZ')}")
            
        except Exception as e:
            print(f"   CRITICAL: Failed to reset delay automatically! {e}")
            print(f"   Please manually send a DELETE to {CHAOS_URL} to restore app health.")

    # Phase 4: Incident Logging
    if start_time and end_time:
        print(f"\nPhase 4: Writing completed incident to durable registry...")
        record = log_incident(
            fault_type="redis_latency",
            target="aiops-app",
            start=start_time,
            end=end_time,
            params={"delay_ms": delay_ms}
        )
        print(f"   Incident recorded successfully with ID: {record['incident_id']}")
        print(f"=========================================")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIOps Chaos Experiment Runner")
    parser.add_argument(
        "--baseline-seconds", 
        type=int, 
        default=30, 
        help="Normal runtime duration before injection (default: 30)"
    )
    parser.add_argument(
        "--duration-seconds", 
        type=int, 
        default=60, 
        help="Active duration of the injected fault (default: 60)"
    )
    parser.add_argument(
        "--delay-ms", 
        type=int, 
        default=500, 
        help="Millisecond delay injected into Redis operations (default: 500)"
    )
    
    args = parser.parse_args()
    
    run_experiment(
        baseline_seconds=args.baseline_seconds,
        duration_seconds=args.duration_seconds,
        delay_ms=args.delay_ms
    )