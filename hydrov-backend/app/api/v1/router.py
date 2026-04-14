# app/api/v1/router.py
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    devices,
    zones,
    telemetry,
    alerts,
)

api_v1_router = APIRouter()

api_v1_router.include_router(auth.router,        prefix="/auth",        tags=["auth"])
api_v1_router.include_router(devices.router,     prefix="/devices",     tags=["devices"])
api_v1_router.include_router(zones.router,       prefix="/zones",       tags=["zones"])
api_v1_router.include_router(telemetry.router,   prefix="/telemetry",   tags=["telemetry"])
api_v1_router.include_router(alerts.router,      prefix="/alerts",      tags=["alerts"])

@api_v1_router.get("/health", tags=["health"])
async def v1_health_check():
    return {"status": "ok", "message": "HYDRO-V API v2.0 is alive!"}
