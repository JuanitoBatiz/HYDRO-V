from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ZoneSchema(BaseModel):
    id: int
    zone_code: str
    name: str
    municipality: str
    state: str
    latitude: float
    longitude: float
    population: Optional[int]
    area_km2: Optional[float]
    created_at: datetime
    
    model_config = {"from_attributes": True}

class ZoneCreateSchema(BaseModel):
    zone_code: str
    name: str
    municipality: str
    state: str
    latitude: float
    longitude: float
    population: Optional[int] = None
    area_km2: Optional[float] = None
