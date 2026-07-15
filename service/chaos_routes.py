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

class DownstreamFailureRequest(BaseModel):
    failure_rate: float = Field(..., ge=0.0, le=1.0)

class CPUBurnRequest(BaseModel):
    workers: int = Field(1, ge=1, le=2)

class MemoryLeakRequest(BaseModel):
    megabytes: int = Field(..., ge=0, le=100)


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



# Downstream Failure Endpoints
@router.post("/downstream-failure", status_code=status.HTTP_200_OK)
async def set_downstream_failure(payload: DownstreamFailureRequest):
    chaos_state.set_downstream_failure_rate(payload.failure_rate)
    return {"downstream_failure_rate": chaos_state.get_downstream_failure_rate()}

@router.delete("/downstream-failure", status_code=status.HTTP_200_OK)
async def delete_downstream_failure():
    chaos_state.reset_downstream_failure()
    return {"downstream_failure_rate": chaos_state.get_downstream_failure_rate()}



# CPU Spike Endpoints
@router.post("/cpu-burn", status_code=status.HTTP_200_OK)
async def set_cpu_burn(payload: CPUBurnRequest):
    active_workers = chaos_state.start_cpu_burn(payload.workers)
    return {"cpu_burn_active": True, "workers": active_workers}

@router.delete("/cpu-burn", status_code=status.HTTP_200_OK)
async def delete_cpu_burn():
    chaos_state.stop_cpu_burn()
    return {"cpu_burn_active": False, "workers": 0}


# Memory Leak Endpoints
@router.post("/memory-leak", status_code=status.HTTP_200_OK)
async def set_memory_leak(payload: MemoryLeakRequest):
    total_allocated = chaos_state.allocate_memory_leak(payload.megabytes)
    return {"memory_leak_active": True, "allocated_mb": total_allocated}

@router.delete("/memory-leak", status_code=status.HTTP_200_OK)
async def delete_memory_leak():
    chaos_state.clear_memory_leak()
    return {"memory_leak_active": False, "allocated_mb": 0}