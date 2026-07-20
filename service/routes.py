from random import random
import time
import uuid
import os
import redis
import asyncio
from redis.exceptions import RedisError
from pydantic import BaseModel
from fastapi import APIRouter, status, HTTPException
from metrics import REDIS_LATENCY, CACHE_COUNT, DOWNSTREAM_CALL_DURATION, DOWNSTREAM_CALLS
import chaos_state  
from logger import logger

class Item(BaseModel):
    name: str
    price: float


class ItemResponse(Item):
    id: str


router = APIRouter()
items: dict[str, Item] = {}

# get url from .env or default to localhost
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(redis_url, decode_responses=True)

# CREATE item
@router.post("/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
async def create_item(item: Item):
    logger.info("POST /items")
    item_id = str(uuid.uuid4())
    items[item_id] = item
    # store item in Redis 
    try:
        # Logger timer
        start = time.time()
        # Start prometheus Redis SET timer
        with REDIS_LATENCY.labels(operation="set").time():
            # if simulated chaos is enabled, inject delay
            delay = chaos_state.get_redis_delay_ms()
            if delay > 0:
                # Convert ms to seconds
                await asyncio.sleep(delay / 1000.0)
            key = f"item:{item_id}"
            logger.info(
                "redis_set",
                extra={
                    "event": "redis_set",
                    "key": key
                }
            )
            r.set(key, item.model_dump_json())
        duration_ms = (time.time() - start) * 1000
        logger.info(
            "redis_set_complete",
            extra={
                "event": "redis_set",
                "duration_ms": duration_ms,
                "success": True
            }
        )
    except RedisError as e:
        CACHE_COUNT.labels(outcome="error").inc()
        logger.error("Redis unavailable: %s", e)
    
    # unpack model and return json response
    return {"id": item_id, **item.model_dump()}

# GET item by ID
@router.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: str):
    logger.info(
        "request_started",
        extra={
            "event": "request",
            "method": "GET",
            "endpoint": "/items"
        }
    )
    # Try Redis cache
    try:
        # Logger timer
        start = time.time()
        # Start prometheus Redis GET timer
        with REDIS_LATENCY.labels(operation="get").time():

            # if simulated chaos is enabled, inject delay
            delay = chaos_state.get_redis_delay_ms()
            if delay > 0:
                # Convert ms to seconds
                await asyncio.sleep(delay / 1000.0) 

            # execute Redis GET command
            key = f"item:{item_id}"
            logger.info(
                "redis_get",
                extra={
                    "event": "redis_get",
                    "key": key
                }
            )
            cached = r.get(key)
        duration_ms = (time.time() - start) * 1000
        logger.info(
            "redis_get_complete",
            extra={
                "event": "redis_get",
                "duration_ms": duration_ms,
                "success": True
            }
        )
        if cached is not None:
            # Increment cache hit counter
            CACHE_COUNT.labels(outcome="hit").inc()
            item = Item.model_validate_json(cached)

            # run downstream
            logger.info(
                "downstream_call",
                extra={
                    "event": "downstream_call",
                    "dependency": "catalog-service"
                }
            )

            start = time.time()
            await call_catalog_service()  
            duration_ms = (time.time() - start) * 1000
            logger.info(
                "downstream_call_complete",
                extra={
                    "event": "downstream_call",
                    "dependency": "catalog-service",
                    "duration_ms": duration_ms,
                    "success": True
                }
            )
            return {"id": item_id, **item.model_dump()}
        else:
            # Increment cache miss counter
            CACHE_COUNT.labels(outcome="miss").inc()
    except RedisError as e:
        CACHE_COUNT.labels(outcome="error").inc()
        logger.error("Redis error on get: %s", e)
    
    # Cache miss or Redis unavailable: hit the fake DB
    time.sleep(0.01) 
    item = items.get(item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Item not found"
        )
    
    # Cache the item for next time
    try:
        # Logger timer
        start = time.time()
        # Start prometheus Redis SET timer
        with REDIS_LATENCY.labels(operation="set").time():
            # if simulated chaos is enabled, inject delay
            delay = chaos_state.get_redis_delay_ms()
            if delay > 0:
                # Convert ms to seconds
                await asyncio.sleep(delay / 1000.0)

            key = f"item:{item_id}"
            logger.info(
                "redis_set",
                extra={
                    "event": "redis_set",
                    "key": key
                }
            )
            r.set(key, item.model_dump_json())

        duration_ms = (time.time() - start) * 1000
        logger.info(
            "redis_set_complete",
            extra={
                "event": "redis_set",
                "duration_ms": duration_ms,
                "success": True
            }
        )
    except RedisError as e:
        CACHE_COUNT.labels(outcome="error").inc()
        logger.error("Redis error on set: %s", e)


    # Simulated downstream dependency call
    logger.info(
        "downstream_call",
        extra={
            "event": "downstream_call",
            "dependency": "catalog-service"
        }
    )

    start = time.time()
    await call_catalog_service()  
    duration_ms = (time.time() - start) * 1000
    logger.info(
                "downstream_call_complete",
                extra={
                    "event": "downstream_call",
                    "dependency": "catalog-service",
                    "duration_ms": duration_ms,
                    "success": True
                }
            )

    return {"id": item_id, **item.model_dump()}

# Simulated Downstream Dependency Call
async def call_catalog_service():
    """
    Simulates an external call to a simulated downstream dependency.
    Wraps the entire execution in the downstream metrics.
    """
    dependency_name = "catalog-service"

    failure_rate = chaos_state.get_downstream_failure_rate()
    if failure_rate > 0.0 and random() < failure_rate:
        DOWNSTREAM_CALLS.labels(dependency=dependency_name, outcome="error").inc()
        logger.error(
            "downstream_failure",
            extra={
                "event": "downstream_failure",
                "dependency": "catalog-service",
                "error": "timeout"
            }
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="catalog service unavailable"
        )

    # Start the timer specifically for the downstream call
    with DOWNSTREAM_CALL_DURATION.labels(dependency=dependency_name).time():
        # 1. Base latency (5ms) + injected chaos delay
        base_delay_s = 0.005 
        chaos_delay_s = chaos_state.get_downstream_delay_ms() / 1000.0
        total_delay = base_delay_s + chaos_delay_s

        try:
            await asyncio.sleep(total_delay)
            DOWNSTREAM_CALLS.labels(dependency=dependency_name, outcome="success").inc()
        except Exception:
            DOWNSTREAM_CALLS.labels(dependency=dependency_name, outcome="error").inc()
            logger.error(
                "downstream_failure",
                extra={
                    "event": "downstream_failure",
                    "dependency": "catalog-service",
                    "error": "timeout"
                }
            )
            raise