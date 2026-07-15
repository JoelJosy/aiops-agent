import gc
import threading

# ===============================
# Redis Delay State Management
# ===============================

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

# ===============================
# Downstream Delay State Management
# ===============================

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

# ===============================
# Downstream Failure State Management
# ===============================

_downstream_failure_rate: float = 0.0
def set_downstream_failure_rate(rate: float):
    global _downstream_failure_rate
    _downstream_failure_rate = max(0.0, min(1.0, rate))

def get_downstream_failure_rate() -> float:
    return _downstream_failure_rate

def reset_downstream_failure():
    global _downstream_failure_rate
    _downstream_failure_rate = 0.0

# ===============================
# CPU Spike State Management
# ===============================
cpu_threads = []
cpu_stop_event = threading.Event()
cpu_lock = threading.Lock()

def start_cpu_burn(workers: int = 1) -> int:
    """Starts up to 2 background CPU worker threads."""
    global cpu_threads
    with cpu_lock:
        # Prevent starting more if threads are already running
        if cpu_threads:
            return len(cpu_threads)
        
        cpu_stop_event.clear()
        workers = max(1, min(2, workers))  # Bound between 1 and 2
        
        def burn_cpu():
            # Infinite math calculations to max out a CPU core
            while not cpu_stop_event.is_set():
                _ = 12345.6789 * 98765.4321

        for _ in range(workers):
            t = threading.Thread(target=burn_cpu, daemon=True)
            t.start()
            cpu_threads.append(t)
            
        return len(cpu_threads)

def stop_cpu_burn():
    """Signals and joins all running CPU worker threads."""
    global cpu_threads
    with cpu_lock:
        cpu_stop_event.set()
        cpu_threads = []

# ===============================
# Memory Leak State Management
# ===============================
# Module-level list to hold references to bytearrays so GC cannot reclaim them
memory_leak_reservoir: list[bytearray] = []

def allocate_memory_leak(mb_to_allocate: int) -> int:
    """Appends bytearrays to simulate a leak, bounded at 100MB per call."""
    global memory_leak_reservoir
    mb_to_allocate = max(0, min(100, mb_to_allocate))
    
    # 1 MB = 1,048,576 bytes
    chunk = bytearray(mb_to_allocate * 1024 * 1024)
    memory_leak_reservoir.append(chunk)
    
    # Return total allocated MB currently held in the leak reservoir
    return sum(len(c) for c in memory_leak_reservoir) // (1024 * 1024)

def clear_memory_leak():
    """Clears the reservoir and runs garbage collection."""
    global memory_leak_reservoir
    memory_leak_reservoir.clear()
    gc.collect()  # Explicitly tell Python to free memory to the OS