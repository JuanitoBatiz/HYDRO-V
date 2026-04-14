from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class AlertResponseSchema(BaseModel):
    id: int
    device_id: int
    sensor_id: Optional[int]
    alert_type_id: int
    severity: str
    confidence_score: Optional[float]
    description: Optional[str]
    payload_snapshot: dict
    detected_at: datetime
    resolved_at: Optional[datetime]
    is_resolved: bool

    model_config = {"from_attributes": True}

class AlertListSchema(BaseModel):
    total: int
    items: list[AlertResponseSchema]

class AlertResolveSchema(BaseModel):
    is_resolved: bool = True