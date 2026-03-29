# app/schemas/telemetry.py
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime, timezone
from typing import Literal


class SensorsSchema(BaseModel):
    turbidity_ntu:     float
    distance_cm:       float
    flow_lpm:          float
    flow_total_liters: float

    # Emma manda los valores como strings desde el ESP32
    # Estos validadores los convierten a float automáticamente
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
    device_id:    str
    timestamp:    int             # millis() del ESP32 — se ignora para almacenamiento
    sensors:      SensorsSchema
    system_state: SystemStateSchema

    # Timestamp real de recepción — lo genera el backend, no el ESP32
    received_at:  datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def validate_device_id(self):
        if not self.device_id.startswith("HYDRO-V-"):
            raise ValueError(f"device_id inválido: '{self.device_id}'. Debe comenzar con 'HYDRO-V-'")
        return self


# ── Schemas de respuesta para endpoints ──────────────────────────

class TelemetryResponseSchema(BaseModel):
    device_id:    str
    received_at:  datetime
    turbidity_ntu: float
    distance_cm:  float
    flow_lpm:     float
    flow_total_liters: float
    state:        str
    intake_cycles: int
    reject_cycles: int
    error_count:  int

    model_config = {"from_attributes": True}


class TelemetryListSchema(BaseModel):
    total:  int
    items:  list[TelemetryResponseSchema]