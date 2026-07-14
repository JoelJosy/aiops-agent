import time
import uuid
from pydantic import BaseModel
from fastapi import APIRouter, status, HTTPException

class Item(BaseModel):
    name: str
    price: float


class ItemResponse(Item):
    id: str

router = APIRouter()
items: dict[str, Item] = {}

# CREATE item
@router.post("/items", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(item: Item):
    item_id = str(uuid.uuid4())
    items[item_id] = item
    # unpack model and return json response
    return {"id": item_id, **item.model_dump()}

# GET item by ID
@router.get("/items/{item_id}", response_model=ItemResponse)
def get_item(item_id: str):
    # Simulate a delay
    time.sleep(0.01) 
    item = items.get(item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Item not found"
        )
    return {"id": item_id, **item.model_dump()}