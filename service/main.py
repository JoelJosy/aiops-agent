from fastapi import FastAPI, Request, Response
from prometheus_client import make_asgi_app
import time
from routes import router
from metrics import REQUEST_COUNT, REQUEST_LATENCY

app = FastAPI(
    title="AIOps Agent Service",
    version="0.1.0",
)

# mount the Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# HTTP middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    # Normalize the path to strip any trailing slashes for the check
    path = request.url.path.rstrip("/")

    # Exclude /metrics from being monitored to avoid scrape noise
    if path == "/metrics":
        return await call_next(request)

    start_time = time.perf_counter()
    # default to 500 in case of unhandled exceptions
    status_code = 500  

    method = request.method
    try:
        # record response status code
        response: Response = await call_next(request)
        status_code = response.status_code
        return response
    finally:
        # calculate request duration and update Prometheus metrics
        duration = time.perf_counter() - start_time

        # Get the generic route template (e.g., /items/{item_id}) instead of the actual ID
        # Falling back to request.url.path if the route doesn't match
        route_info = request.scope.get("route")
        if route_info:
            endpoint = route_info.path
        else:
            endpoint = request.url.path

        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(duration)
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, http_status=status_code).inc()

app.include_router(router)

@app.get("/health")
def health_check():
    return {"status": "healthy"}