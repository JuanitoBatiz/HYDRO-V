# app/schemas/__init__.py
from app.schemas.telemetry import (
    ESP32PayloadSchema,
    SensorsSchema,
    SystemStateSchema,
    TelemetryResponseSchema,
    TelemetryListSchema,
)
from app.schemas.alert import (
    AlertResponseSchema,
    AlertListSchema,
    AlertResolveSchema,
)
from app.schemas.device import (
    DeviceCreateSchema,
    DeviceUpdateSchema,
    DeviceResponseSchema,
)
from app.schemas.user import (
    UserCreateSchema,
    UserLoginSchema,
    UserResponseSchema,
    TokenSchema,
    TokenPayloadSchema,
)

__all__ = [
    "ESP32PayloadSchema",
    "SensorsSchema",
    "SystemStateSchema",
    "TelemetryResponseSchema",
    "TelemetryListSchema",
    "AlertResponseSchema",
    "AlertListSchema",
    "AlertResolveSchema",
    "DeviceCreateSchema",
    "DeviceUpdateSchema",
    "DeviceResponseSchema",
    "UserCreateSchema",
    "UserLoginSchema",
    "UserResponseSchema",
    "TokenSchema",
    "TokenPayloadSchema",
]