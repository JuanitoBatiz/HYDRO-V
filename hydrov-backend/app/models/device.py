from sqlalchemy import Integer, String, Float, DateTime, ForeignKey, CheckConstraint, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from datetime import datetime
from sqlalchemy.sql import func

class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"), nullable=False, index=True)
    device_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, CheckConstraint("latitude >= -90 AND latitude <= 90", name="chk_device_b04225"), nullable=False)
    longitude: Mapped[float] = mapped_column(Float, CheckConstraint("longitude >= -180 AND longitude <= 180", name="chk_device_f06d62"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), CheckConstraint("status IN ('active', 'inactive', 'maintenance')", name="chk_device_069243"), nullable=False, index=True)
    firmware_version: Mapped[str] = mapped_column(String(20), nullable=False)
    cistern_capacity_liters: Mapped[float] = mapped_column(Float, CheckConstraint("cistern_capacity_liters > 0", name="chk_device_f5aa89"), default=3400.0, server_default="3400.0", nullable=False)
    cistern_height_cm: Mapped[float] = mapped_column(Float, CheckConstraint("cistern_height_cm > 0", name="chk_device_e14215"), default=125.0, server_default="125.0", nullable=False)
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # Relaciones
    telemetry_events:     Mapped[list["TelemetryEvent"]]     = relationship("TelemetryEvent",     back_populates="device")
    emergency_alerts:     Mapped[list["EmergencyAlert"]]     = relationship("EmergencyAlert",     back_populates="device")
    # autonomy_predictions: Mapped[list["AutonomyPrediction"]] = relationship("AutonomyPrediction", back_populates="device")
    # leak_detections:      Mapped[list["LeakDetection"]]      = relationship("LeakDetection",      back_populates="device")