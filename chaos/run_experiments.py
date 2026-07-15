import argparse
import subprocess
import time
from datetime import datetime, timezone
import requests
from incident_logger import log_incident

# Configuration
APP_URL = "http://localhost:8000"
CHAOS_URL = f"{APP_URL}/chaos/redis-delay"
DOWNSTREAM_CHAOS_URL = f"{APP_URL}/chaos/downstream-delay"
HEALTH_URL = f"{APP_URL}/health"


def poll_health(timeout_seconds: int = 60) -> bool:
    """
    Repeatedly polls the /health endpoint until it returns 200 OK.
    Handles connection errors gracefully while the container is spinning up.
    """
    print(f"Polling {HEALTH_URL} until it returns 200 OK...")
    start_poll = time.time()
    
    while time.time() - start_poll < timeout_seconds:
        try:
            response = requests.get(HEALTH_URL, timeout=2)
            if response.status_code == 200:
                print("Health check passed! Uvicorn is ready to accept traffic.")
                return True
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            # Safe to ignore; the container or server is still starting up
            pass
        
        time.sleep(1)
        
    raise TimeoutError(f"App did not become healthy within {timeout_seconds} seconds.")

def poll_redis(timeout_seconds: int = 60) -> bool:
    """
    Repeatedly executes 'redis-cli ping' inside the Redis container
    until it successfully returns 'PONG'.
    """
    print("Polling Redis container with 'redis-cli ping' until it returns PONG...")
    start_poll = time.time()
    
    while time.time() - start_poll < timeout_seconds:
        try:
            # -T disables pseudo-TTY allocation, essential for non-interactive scripts
            result = subprocess.run(
                ["docker", "compose", "exec", "-T", "redis", "redis-cli", "ping"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # Check if the output contains the standard Redis "PONG" response
            if "PONG" in result.stdout:
                print("   Redis is healthy and responding to commands!")
                return True
        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            # Safe to ignore; Redis is still booting up
            pass
        
        time.sleep(1)
        
    raise TimeoutError(f"Redis did not become healthy within {timeout_seconds} seconds.")


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

    # Write to incidents log
    log_incident(
        fault_type="redis_latency",
        target="aiops-app",
        start=start_time,
        end=end_time,
        params={"delay_ms": delay_ms}
    )

def run_outage_experiment(duration_seconds: int):
    """Executes a real app container outage via Docker Compose."""
    start_time = None
    end_time = None

    try:
        print(f"\nStopping {args.target} container...")
        # Use subprocess to stop the app container
        subprocess.run(["docker", "compose", "stop", "aiops-app"], check=True)
        
        start_time = datetime.now(timezone.utc)
        print(f"   Outage started at: {start_time.strftime('%H:%M:%SZ')}")
        print(f"   Monitoring outage period for {duration_seconds} seconds...")
        time.sleep(duration_seconds)

    finally:
        # Guaranteed to run in finally block so your stack isn't left broken!
        print(f"\nRestarting {args.target} container...")
        subprocess.run(["docker", "compose", "start", "aiops-app"], check=True)
        
        # Wait for the python app inside the container to actually respond to HTTP traffic
        poll_health()
        
        end_time = datetime.now(timezone.utc)
        print(f"   Outage recovery complete at: {end_time.strftime('%H:%M:%SZ')}")

    # Write to incidents log
    log_incident(
        fault_type="app_outage",
        target="aiops-app",
        start=start_time,
        end=end_time,
        params={}
    )

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
        params={}
    )

def run_downstream_latency_experiment(duration_seconds: int, delay_ms: int):
    """Executes a simulated downstream catalog-service latency injection."""
    start_time = None
    end_time = None
    try:
        print(f"\nInjecting Downstream Dependency Latency...")
        print(f"   POST {DOWNSTREAM_CHAOS_URL} with delay_ms={delay_ms}")
        response = requests.post(DOWNSTREAM_CHAOS_URL, json={"delay_ms": delay_ms})
        response.raise_for_status()

        start_time = datetime.now(timezone.utc)
        print(f"   Fault injected at: {start_time.strftime('%H:%M:%SZ')}")
        print(f"   Monitoring fault period for {duration_seconds} seconds...")
        time.sleep(duration_seconds)
    finally:
        print(f"\nHealing System (Resetting downstream delay to 0)...")
        response = requests.delete(DOWNSTREAM_CHAOS_URL)
        response.raise_for_status()
        end_time = datetime.now(timezone.utc)
        print(f"   System healed at: {end_time.strftime('%H:%M:%SZ')}")

    log_incident(
        fault_type="downstream_latency",
        target="aiops-app",
        start=start_time,
        end=end_time,
        params={
            "dependency": "catalog-service",
            "delay_ms": delay_ms
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AIOps Chaos Experiment Runner")
    parser.add_argument(
        "--fault",
        type=str,
        required=True,
        choices=["redis_latency", "app_outage", "redis_outage", "downstream_latency"],
        help="The type of fault to inject into the system"
    )
    parser.add_argument(
        "--target",
        type=str,
        default="aiops-app",
        help="Target container/service (default: aiops-app)"
    )
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
        help="Active duration of the injected fault"
    )
    parser.add_argument(
        "--delay-ms", 
        type=int, 
        default=500, 
        help="Millisecond delay (only used for redis_latency)"
    )
    
    args = parser.parse_args()
    
    print(f"Starting Chaos Experiment Runner")
    print(f"=========================================")
    print(f"Phase 1: Baseline Period ({args.baseline_seconds} seconds)")
    print(f"   Waiting for system to gather normal metric traffic...")
    time.sleep(args.baseline_seconds)
    
    if args.fault == "redis_latency":
        run_latency_experiment(args.duration_seconds, args.delay_ms)
    elif args.fault == "app_outage":
        run_outage_experiment(args.duration_seconds)
    elif args.fault == "redis_outage":
        run_redis_outage_experiment(args.duration_seconds)
    elif args.fault == "downstream_latency":
        run_downstream_latency_experiment(args.duration_seconds, args.delay_ms)
        
    print(f"=========================================")