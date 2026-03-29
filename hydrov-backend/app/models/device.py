# app/models/device.py
from sqlalchemy import String, Float, Boolean, DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from datetime import datetime
from typing import Optional


class Device(Base):
    __tablename__ = "devices"

    id:           Mapped[int]            = mapped_column(Integer, primary_key=True, index=True)
    device_id:    Mapped[str]            = mapped_column(String(50), unique=True, nullable=False, index=True)  # "HYDRO-V-001"
    name:         Mapped[str]            = mapped_column(String(100), nullable=False)
    lat:          Mapped[float]          = mapped_column(Float, nullable=False)
    lon:          Mapped[float]          = mapped_column(Float, nullable=False)
    location:     Mapped[Optional[str]]  = mapped_column(String(200), nullable=True)
    roof_area_m2: Mapped[float]          = mapped_column(Float, nullable=False)  # para cálculo de captación
    is_active:    Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    last_seen:    Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:   Mapped[datetime]       = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relaciones
    telemetry_events:     Mapped[list["TelemetryEvent"]]     = relationship("TelemetryEvent",     back_populates="device")
    emergency_alerts:     Mapped[list["EmergencyAlert"]]     = relationship("EmergencyAlert",     back_populates="device")
    autonomy_predictions: Mapped[list["AutonomyPrediction"]] = relationship("AutonomyPrediction", back_populates="device")
    leak_detections:      Mapped[list["LeakDetection"]]      = relationship("LeakDetection",      back_populates="device")