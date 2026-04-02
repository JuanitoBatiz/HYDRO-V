# app/schemas/mqtt.py
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from datetime import datetime, timezone
from typing import Literal

class SensorsSchema(BaseModel):
    turbidity_ntu:     float
    distance_cm:       float
    flow_lpm:          float
    flow_total_liters: float

    @field_validator("turbidity_ntu", "distance_cm", "flow_lpm", "flow_total_liters", mode="before")
    @classmethod
    def parse_string_to_float(cls, v):
        try:
            return float(v)
        except (ValueError, TypeError):
            raise ValueError(f"No se puede convertir '{v}' a float")

    @field_validator("turbidity_ntu", "distance_cm", "flow_lpm", "flow_total_liters")
    @classmethod
    def must_be_non_negative(cls, v):
        if v < 0:
            raise ValueError("Los valores de sensor no pueden ser negativos")
        return v

class SystemStateSchema(BaseModel):
    state:            Literal["IDLE", "ANALYZING", "HARVESTING", "FULL_TANK", "EMERGENCY"]
    state_duration_ms: int = Field(ge=0)
    intake_cycles:    int  = Field(ge=0)
    reject_cycles:    int  = Field(ge=0)
    error_count:      int  = Field(ge=0)

class ESP32PayloadSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    device_code:  str = Field(alias="device_id")  # Mapear de 'device_id' a 'device_code'
    timestamp:    int
    sensors:      SensorsSchema
    system_state: SystemStateSchema

    received_at:  datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_device_id(self):
        if not self.device_code.startswith("HYDRO-V-"):
            raise ValueError(f"device_code inválido: '{self.device_code}'. Debe comenzar con 'HYDRO-V-'")
        return self
