# app/models/alert.py
from sqlalchemy import String, Integer, DateTime, Boolean, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base
from datetime import datetime
from typing import Optional


class EmergencyAlert(Base):
    __tablename__ = "emergency_alerts"

    id:                Mapped[int]           = mapped_column(Integer, primary_key=True, index=True)
    node_id:           Mapped[str]           = mapped_column(String(50), ForeignKey("devices.device_id"), nullable=False, index=True)
    timestamp:         Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    error_count:       Mapped[int]           = mapped_column(Integer, nullable=False)
    state_duration_ms: Mapped[int]           = mapped_column(Integer, nullable=False)
    payload_snapshot:  Mapped[dict]          = mapped_column(JSONB, nullable=False)  # JSON completo del ESP32
    resolved:          Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    resolved_notes:    Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_at:       Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at:        Mapped[datetime]      = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relación
    device: Mapped["Device"] = relationship("Device", back_populates="emergency_alerts")