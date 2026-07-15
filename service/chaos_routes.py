from fastapi import APIRouter, status
from pydantic import BaseModel, Field
import chaos_state


router = APIRouter(prefix="/chaos", tags=["chaos injection"])

# Pydantic model to validate user input (restricts delay between 0 and 2 seconds)
class DelayRequest(BaseModel):
    delay_ms: int = Field(
        ..., 
        ge=0, 
        le=2000, 
        description="The simulated latency to add to Redis calls in milliseconds"
    )

# Redis Delay Endpoints
@router.post("/redis-delay", status_code=status.HTTP_200_OK)
def set_delay(request: DelayRequest):
    """Sets the simulated Redis delay in milliseconds."""
    chaos_state.set_redis_delay_ms(request.delay_ms)
    return {"redis_delay_ms": chaos_state.get_redis_delay_ms()}

@router.delete("/redis-delay", status_code=status.HTTP_200_OK)
async def delete_delay():
    """Resets simulated Redis delay back to 0ms."""
    chaos_state.reset_redis_delay()
    return {"redis_delay_ms": chaos_state.get_redis_delay_ms()}

# Downstream Delay Endpoints
@router.post("/downstream-delay", status_code=status.HTTP_200_OK)
async def set_downstream_delay(payload: DelayRequest):
    """Injects simulated latency into downstream dependency calls."""
    chaos_state.set_downstream_delay_ms(payload.delay_ms)
    return {"downstream_delay_ms": chaos_state.get_downstream_delay_ms()}

@router.delete("/downstream-delay", status_code=status.HTTP_200_OK)
async def delete_downstream_delay():
    """Resets simulated downstream delay back to 0ms."""
    chaos_state.reset_downstream_delay()
    return {"downstream_delay_ms": chaos_state.get_downstream_delay_ms()}