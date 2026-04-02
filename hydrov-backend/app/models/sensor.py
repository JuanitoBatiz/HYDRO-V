from sqlalchemy import Integer, Boolean, Float, DateTime, ForeignKey, CheckConstraint, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from datetime import datetime

class Sensor(Base):
    __tablename__ = "sensors"
    __table_args__ = (
        CheckConstraint("min_threshold <= max_threshold", name="chk_sensor_thresholds"),
        UniqueConstraint("device_id", "sensor_type_id", name="idx_sensors_device_type")
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), nullable=False)
    sensor_type_id: Mapped[int] = mapped_column(ForeignKey("sensor_types.id"), nullable=False)
    min_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    max_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    installed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
