# app/schemas/device.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class DeviceCreateSchema(BaseModel):
    device_id:   str = Field(pattern=r"^HYDRO-V-\d{3}$")  # HYDRO-V-001, HYDRO-V-002...
    name:        str = Field(max_length=100)
    lat:         float = Field(ge=-90,  le=90)
    lon:         float = Field(ge=-180, le=180)
    location:    Optional[str] = Field(None, max_length=200)
    roof_area_m2: float = Field(gt=0, description="Área de captación del techo en m²")


class DeviceUpdateSchema(BaseModel):
    name:         Optional[str]  = Field(None, max_length=100)
    location:     Optional[str]  = Field(None, max_length=200)
    roof_area_m2: Optional[float] = Field(None, gt=0)
    is_active:    Optional[bool]  = None


class DeviceResponseSchema(BaseModel):
    id:           int
    device_id:    str
    name:         str
    lat:          float
    lon:          float
    location:     Optional[str]
    roof_area_m2: float
    is_active:    bool
    created_at:   datetime
    last_seen:    Optional[datetime]

    model_config = {"from_attributes": True}