from prometheus_client import Counter, Histogram, make_asgi_app


REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Latency of HTTP requests in seconds",
    ["method", "endpoint"],
)

REQUEST_COUNT = Counter(
    "http_request_total",  
    "Total number of HTTP requests",
    ["method", "endpoint", "http_status"],
)

REDIS_LATENCY = Histogram(
    "redis_request_duration_seconds",
    "Latency of Redis requests in seconds",
    # get / set
    ["operation"],
)

CACHE_COUNT = Counter(
    "cache_request_total",
    "Cache hit, miss, and error counts",
    ["outcome"],
)


DOWNSTREAM_CALL_DURATION = Histogram(
    "downstream_call_duration_seconds",
    "Latency of downstream dependency calls in seconds",
    ["dependency"]
)

DOWNSTREAM_CALLS = Counter(
    "downstream_calls_total",
    "Total number of downstream dependency calls",
    ["dependency", "outcome"]
)