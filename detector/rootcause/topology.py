
# Which metrics can plausibly be the ROOT CAUSE of which other metrics moving.
# Resource metrics (CPU/memory) are causal-only — nothing in this app causes them.

DEPENDENCY_PRIOR = {
    # Resource exhaustion
    "process_cpu_rate": {
        "can_cause": [
            "app_p95_latency_seconds",
            "app_error_rate",
        ]
    },

    "process_resident_memory_bytes": {
        "can_cause": [
            "process_cpu_rate",          # GC / paging pressure
            "app_p95_latency_seconds",
            "app_error_rate",
        ]
    },

    # Cache problems
    "redis_average_latency_seconds": {
        "can_cause": [
            "cache_error_rate",
            "app_p95_latency_seconds",
        ]
    },

    "cache_error_rate": {
        "can_cause": [
            "app_error_rate",
            "app_availability",
        ]
    },

    # Downstream dependency problems
    "downstream_average_latency_seconds": {
        "can_cause": [
            "downstream_error_rate",
            "app_p95_latency_seconds",
        ]
    },

    "downstream_error_rate": {
        "can_cause": [
            "app_error_rate",
            "app_availability",
        ]
    },

    # Application layer
    "app_p95_latency_seconds": {
        "can_cause": [
            "app_error_rate",
            "app_availability",
        ]
    },

    "app_error_rate": {
        "can_cause": [
            "app_availability",
        ]
    },

    # Context only
    "request_rate": {
        "can_cause": []
    },

    # Terminal
    "app_availability": {
        "can_cause": []
    },
}