from pydantic import BaseModel, Field
from typing import Any, Optional

class StartOrderRequest(BaseModel):
    payment_id: str = Field(..., min_length=1)
    address: dict = Field(default_factory=dict)

class UpdateAddressRequest(BaseModel):
    address: dict

class StatusResponse(BaseModel):
    workflow: dict
    events: list[dict[str, Any]]
    db_order: Optional[dict] = None


