# Redis Delay State Management
# Internal private variable to hold delay state (starts at 0ms)
_redis_delay_ms: int = 0

def set_redis_delay_ms(delay_ms: int):
    """Sets the simulated Redis delay in milliseconds."""
    global _redis_delay_ms
    _redis_delay_ms = delay_ms

def get_redis_delay_ms() -> int:
    """Retrieves the current simulated Redis delay."""
    return _redis_delay_ms

def reset_redis_delay():
    """Resets the delay back to 0."""
    global _redis_delay_ms
    _redis_delay_ms = 0

# Downstream Delay State Management
_downstream_delay_ms: int = 0
def set_downstream_delay_ms(delay_ms: int):
    """Sets the simulated downstream dependency delay in milliseconds."""
    global _downstream_delay_ms
    _downstream_delay_ms = delay_ms

def get_downstream_delay_ms() -> int:
    """Retrieves the current simulated downstream dependency delay."""
    return _downstream_delay_ms

def reset_downstream_delay():
    """Resets the downstream delay back to 0."""
    global _downstream_delay_ms
    _downstream_delay_ms = 0

# Downstream Failure State Management
_downstream_failure_rate: float = 0.0
def set_downstream_failure_rate(rate: float):
    global _downstream_failure_rate
    _downstream_failure_rate = max(0.0, min(1.0, rate))

def get_downstream_failure_rate() -> float:
    return _downstream_failure_rate

def reset_downstream_failure():
    global _downstream_failure_rate
    _downstream_failure_rate = 0.0