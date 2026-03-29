# app/models/telemetry.py
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from datetime import datetime


class TelemetryEvent(Base):
    __tablename__ = "telemetry_events"

    id:               Mapped[int]      = mapped_column(Integer, primary_key=True, index=True)
    device_id:        Mapped[str]      = mapped_column(String(50), ForeignKey("devices.device_id"), nullable=False, index=True)
    received_at:      Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)

    # Sensores
    turbidity_ntu:     Mapped[float]   = mapped_column(Float, nullable=False)
    distance_cm:       Mapped[float]   = mapped_column(Float, nullable=False)
    flow_lpm:          Mapped[float]   = mapped_column(Float, nullable=False)
    flow_total_liters: Mapped[float]   = mapped_column(Float, nullable=False)

    # Estado FSM
    state:             Mapped[str]     = mapped_column(String(20), nullable=False)
    state_duration_ms: Mapped[int]     = mapped_column(Integer, nullable=False)
    intake_cycles:     Mapped[int]     = mapped_column(Integer, nullable=False)
    reject_cycles:     Mapped[int]     = mapped_column(Integer, nullable=False)
    error_count:       Mapped[int]     = mapped_column(Integer, nullable=False)

    # Metadata
    esp32_uptime_ms:   Mapped[int]     = mapped_column(Integer, nullable=False)  # timestamp millis() del ESP32
    created_at:        Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relación
    device: Mapped["Device"] = relationship("Device", back_populates="telemetry_events")