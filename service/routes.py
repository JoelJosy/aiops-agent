import time
import uuid
import os
import redis
from redis.exceptions import RedisError
from pydantic import BaseModel
from fastapi import APIRouter, status, HTTPException

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
def create_item(item: Item):
    item_id = str(uuid.uuid4())
    items[item_id] = item
    # store item in Redis 
    try:
        r.set(f"item:{item_id}", item.model_dump_json())
    except RedisError as e:
        print(f"Redis unavailable: {e}")
    
    # unpack model and return json response
    return {"id": item_id, **item.model_dump()}

# GET item by ID
@router.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: str):
    # Try Redis cache
    try:
        cached = r.get(f"item:{item_id}")
        if cached is not None:
            item = Item.model_validate_json(cached)
            return {"id": item_id, **item.model_dump()}
    except RedisError as e:
        print(f"Redis error on get: {e}")
    
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
        r.set(f"item:{item_id}", item.model_dump_json())
    except RedisError as e:
        print(f"Redis error on set: {e}")
    
    return {"id": item_id, **item.model_dump()}