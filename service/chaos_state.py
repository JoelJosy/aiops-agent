# Internal private variable to hold our delay state (starts at 0ms)
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