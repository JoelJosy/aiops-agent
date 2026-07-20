import subprocess
import time

import requests
from service.logger import logger


APP_URL = "http://localhost:8000"
CHAOS_URL = f"{APP_URL}/chaos/redis-delay"
DOWNSTREAM_CHAOS_URL = f"{APP_URL}/chaos/downstream-delay"
DOWNSTREAM_FAILURE_URL = f"{APP_URL}/chaos/downstream-failure"
CPU_BURN_URL = f"{APP_URL}/chaos/cpu-burn"
MEMORY_LEAK_URL = f"{APP_URL}/chaos/memory-leak"
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
                timeout=5,
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