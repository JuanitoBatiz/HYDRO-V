# app/schemas/device.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class DeviceCreateSchema(BaseModel):
    device_code: str = Field(pattern=r"^HV-[A-Z]{3}-\d{3}$", description="Código del dispositivo, ej: HV-NEZ-001")
    zone_id:     int = Field(description="ID de la zona a la que pertenece")
    latitude:    float = Field(ge=-90,  le=90)
    longitude:   float = Field(ge=-180, le=180)
    firmware_version: str = Field(max_length=20)
    status:      str = Field(default="active")
    cistern_capacity_liters: float = Field(default=1100.0, gt=0)
    cistern_height_cm: float = Field(default=120.0, gt=0)

class DeviceUpdateSchema(BaseModel):
    latitude:    Optional[float] = Field(None, ge=-90, le=90)
    longitude:   Optional[float] = Field(None, ge=-180, le=180)
    status:      Optional[str] = None
    firmware_version: Optional[str] = None
    cistern_capacity_liters: Optional[float] = Field(None, gt=0)
    cistern_height_cm: Optional[float] = Field(None, gt=0)

class DeviceResponseSchema(BaseModel):
    id:           int
    zone_id:      int
    device_code:  str
    latitude:     float
    longitude:    float
    status:       str
    firmware_version: str
    cistern_capacity_liters: float
    cistern_height_cm: float
    installed_at: datetime
    last_seen_at: Optional[datetime]

    model_config = {"from_attributes": True}