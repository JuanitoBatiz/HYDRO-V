# app/schemas/alert.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class EmergencyAlertCreateSchema(BaseModel):
    """Schema interno — lo usa mqtt_service al detectar EMERGENCY."""
    node_id:          str
    timestamp:        datetime
    error_count:      int
    state_duration_ms: int
    payload_snapshot: dict     # JSON completo del ESP32 en el momento del fallo


class EmergencyAlertResponseSchema(BaseModel):
    """Schema de respuesta para el endpoint GET /alerts."""
    id:               int
    node_id:          str
    timestamp:        datetime
    error_count:      int
    state_duration_ms: int
    resolved:         bool
    created_at:       datetime

    model_config = {"from_attributes": True}


class AlertListSchema(BaseModel):
    total:  int
    items:  list[EmergencyAlertResponseSchema]


class AlertResolveSchema(BaseModel):
    """Para marcar una alerta como resuelta desde el frontend."""
    resolved: bool = True
    notes:    Optional[str] = Field(None, max_length=500)